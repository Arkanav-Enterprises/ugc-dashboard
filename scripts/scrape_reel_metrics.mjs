#!/usr/bin/env node
/**
 * scrape_reel_metrics.mjs — CDP-based Instagram reel metrics scraper.
 *
 * Connects to a running Chrome instance via CDP, navigates to each account's
 * reels page, and extracts view counts, likes, captions, and metadata.
 *
 * Usage:
 *   node scripts/scrape_reel_metrics.mjs                              # All 7 accounts
 *   node scripts/scrape_reel_metrics.mjs --account aliyah.manifests   # Single account
 *   node scripts/scrape_reel_metrics.mjs --max-reels 5                # Limit per account
 *
 * Requires: Chrome running with --remote-debugging-port=9222
 */

import { writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import http from "http";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, "..");
const OUTPUT_DIR = join(PROJECT_ROOT, "output", "reel_metrics");

const ACCOUNTS = [
  "aliyah.manifests",
  "aliyah.journals",
  "riley.manifests",
  "riley.journals",
  "sanyahealing",
  "sophie.unplugs",
  "emillywilks",
];

const CDP_PORT = 9222;
const DEFAULT_MAX_REELS = 30;

// ---------------------------------------------------------------------------
// CDP helpers
// ---------------------------------------------------------------------------

let msgId = 1;
let ws = null;
const pending = new Map();

function cdpSend(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = msgId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        if (!data || res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode} from ${url} (empty: ${!data})`));
          return;
        }
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error(`Invalid JSON from ${url}: ${data.slice(0, 100)}`)); }
      });
      res.on("error", reject);
    }).on("error", (err) => {
      reject(new Error(`Cannot connect to Chrome CDP on port ${CDP_PORT}. ` +
        `Make sure Chrome is running with: --remote-debugging-port=${CDP_PORT}\n` +
        `(Quit Chrome fully first — Cmd+Q — then relaunch with the flag)`));
    });
  });
}

async function connectCDP() {
  // Try both endpoints — older Chrome uses /json, newer uses /json/list
  let json;
  try {
    json = await fetchJSON(`http://127.0.0.1:${CDP_PORT}/json/list`);
  } catch {
    json = await fetchJSON(`http://127.0.0.1:${CDP_PORT}/json`);
  }

  const target = json.find((t) => t.type === "page") || json[0];
  if (!target) throw new Error("No Chrome tab found. Is Chrome running with --remote-debugging-port=9222?");

  const wsUrl = target.webSocketDebuggerUrl;
  const { WebSocket } = await import("ws");
  ws = new WebSocket(wsUrl);

  await new Promise((resolve, reject) => {
    ws.on("open", resolve);
    ws.on("error", reject);
  });

  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message));
      else resolve(msg.result);
    }
  });

  await cdpSend("Runtime.enable");
  await cdpSend("Page.enable");
}

async function navigate(url) {
  await cdpSend("Page.navigate", { url });
  await sleep(3000); // Wait for page load
}

async function evaluate(expression) {
  const result = await cdpSend("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(`eval error: ${result.exceptionDetails.text}`);
  }
  return result.result.value;
}

// ---------------------------------------------------------------------------
// Parsing helpers
// ---------------------------------------------------------------------------

function parseViewCount(text) {
  if (!text) return 0;
  text = text.trim().toLowerCase().replace(/,/g, "");
  if (text.endsWith("k")) return Math.round(parseFloat(text) * 1000);
  if (text.endsWith("m")) return Math.round(parseFloat(text) * 1000000);
  return parseInt(text, 10) || 0;
}

function parseLikeCount(text) {
  return parseViewCount(text); // Same format
}

function parseRelativeDate(text) {
  if (!text) return todayStr();
  text = text.trim().toLowerCase();

  const now = new Date();
  const match = text.match(/(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago/);
  if (match) {
    const n = parseInt(match[1], 10);
    const unit = match[2];
    const ms = {
      second: 1000,
      minute: 60000,
      hour: 3600000,
      day: 86400000,
      week: 604800000,
      month: 2592000000,
      year: 31536000000,
    };
    const d = new Date(now.getTime() - n * (ms[unit] || 0));
    return d.toISOString().slice(0, 10);
  }

  // Try direct date parse
  const d = new Date(text);
  if (!isNaN(d.getTime())) return d.toISOString().slice(0, 10);

  return todayStr();
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Scraping logic
// ---------------------------------------------------------------------------

async function scrapeReelGrid(account, maxReels) {
  console.log(`\n📋 Scraping reel grid for @${account}...`);
  await navigate(`https://www.instagram.com/${account}/reels/`);
  await sleep(4000);

  // Check if we got reel links — if not, reload and wait longer
  const hasReels = await evaluate(`document.querySelectorAll('a[href*="/reel/"]').length`);
  if (!hasReels) {
    console.log(`  ⏳ No reels found on first load, reloading...`);
    await cdpSend("Page.reload");
    await sleep(5000);
  }

  // Scroll and collect reel links + view counts from grid.
  // Grid text for each reel link looks like: "10View count icon117"
  // The LAST numeric span is the view count. Earlier numbers are likes/comments.
  const reelStubs = await evaluate(`
    (async () => {
      const reels = [];
      const seen = new Set();
      let scrollAttempts = 0;
      const maxScrolls = ${Math.ceil(maxReels / 3) + 5};

      while (reels.length < ${maxReels} && scrollAttempts < maxScrolls) {
        const links = document.querySelectorAll('a[href*="/reel/"]');
        for (const link of links) {
          const href = link.getAttribute('href');
          const idMatch = href.match(/\\/reel\\/([^/]+)/);
          if (!idMatch || seen.has(idMatch[1])) continue;
          seen.add(idMatch[1]);

          // Collect all numeric spans — the LAST one is the view count
          const spans = link.querySelectorAll('span');
          const numericValues = [];
          for (const span of spans) {
            const text = span.textContent.trim();
            if (text && /^[\\d,.]+[KkMm]?$/.test(text)) {
              numericValues.push(text);
            }
          }
          // View count is the last numeric value (after "View count icon" text)
          const views = numericValues.length > 0 ? numericValues[numericValues.length - 1] : '0';
          // Likes are the first numeric value (if multiple exist)
          const likes = numericValues.length > 1 ? numericValues[0] : '0';

          reels.push({
            id: idMatch[1],
            url: 'https://www.instagram.com' + href,
            gridViews: views,
            gridLikes: likes,
          });
          if (reels.length >= ${maxReels}) break;
        }

        window.scrollBy(0, 800);
        await new Promise(r => setTimeout(r, 1500));
        scrollAttempts++;
      }
      return JSON.stringify(reels);
    })()
  `);

  return JSON.parse(reelStubs);
}

async function scrapeReelDetail(stub) {
  console.log(`  → Scraping reel ${stub.id}...`);
  await navigate(stub.url);
  await sleep(3000);

  // Extract from Instagram's embedded JSON in xdt_api__v1__media__shortcode__web_info.
  // This contains: caption.text, like_count, taken_at, comment_count.
  // Note: view_count is null for creator accounts — we use grid views instead.
  const detail = await evaluate(`
    (() => {
      const result = {
        likes: '0',
        caption: '',
        hashtags: [],
        timestamp: '',
        audio: '',
      };

      // Find the script containing shortcode web info and parse it properly
      const scripts = document.querySelectorAll('script[type="application/json"]');
      for (const script of scripts) {
        const raw = script.textContent || '';
        if (!raw.includes('xdt_api__v1__media__shortcode__web_info')) continue;

        try {
          const data = JSON.parse(raw);
          // Deep-search for the media item object
          const str = JSON.stringify(data);

          // Find caption object and parse it out
          const capIdx = str.indexOf('"caption":{');
          if (capIdx !== -1) {
            // Extract the caption object substring and parse it
            let depth = 0, start = capIdx + 10, end = start;
            for (let i = start; i < str.length && i < start + 2000; i++) {
              if (str[i] === '{') depth++;
              if (str[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
            }
            try {
              const capObj = JSON.parse(str.slice(start, end));
              if (capObj.text) {
                result.caption = capObj.text.slice(0, 500);
              }
            } catch(e) {}
          }

          // Find like_count
          const likeIdx = str.indexOf('"like_count":');
          if (likeIdx !== -1) {
            const numStr = str.slice(likeIdx + 13, likeIdx + 25);
            const m = numStr.match(/^(\\d+)/);
            if (m) result.likes = m[1];
          }

          // Find taken_at
          const taIdx = str.indexOf('"taken_at":');
          if (taIdx !== -1) {
            const numStr = str.slice(taIdx + 11, taIdx + 25);
            const m = numStr.match(/^(\\d+)/);
            if (m) {
              const d = new Date(parseInt(m[1]) * 1000);
              result.timestamp = d.toISOString().slice(0, 10);
            }
          }
        } catch(e) {}

        break;
      }

      // Hashtags from caption
      const hashtagMatches = result.caption.match(/#\\w+/g);
      if (hashtagMatches) result.hashtags = hashtagMatches;

      // Timestamp fallback — DOM time element
      if (!result.timestamp) {
        const timeEl = document.querySelector('time');
        if (timeEl) {
          result.timestamp = timeEl.getAttribute('datetime') || timeEl.textContent.trim();
        }
      }

      // Audio — from link to /audio/ or /music/
      const audioLinks = document.querySelectorAll('a[href*="/audio/"], a[href*="/music/"]');
      for (const link of audioLinks) {
        const text = link.textContent.trim();
        if (text && text.length > 2) {
          result.audio = text;
          break;
        }
      }

      return JSON.stringify(result);
    })()
  `);

  return JSON.parse(detail);
}

async function scrapeAccount(account, maxReels) {
  const stubs = await scrapeReelGrid(account, maxReels);
  console.log(`  Found ${stubs.length} reels in grid`);

  const reels = [];
  for (const stub of stubs) {
    try {
      const detail = await scrapeReelDetail(stub);
      reels.push({
        id: stub.id,
        url: stub.url,
        views: parseViewCount(stub.gridViews),  // Grid is the source of truth for views
        likes: parseLikeCount(detail.likes) || parseViewCount(stub.gridLikes),
        caption: detail.caption,
        hashtags: detail.hashtags,
        timestamp: detail.timestamp || todayStr(),
        audio: detail.audio,
      });
    } catch (err) {
      console.error(`  ⚠ Failed to scrape reel ${stub.id}: ${err.message}`);
      reels.push({
        id: stub.id,
        url: stub.url,
        views: parseViewCount(stub.gridViews),
        likes: parseViewCount(stub.gridLikes),
        caption: "",
        hashtags: [],
        timestamp: todayStr(),
        audio: "",
      });
    }
  }

  return reels;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);
  let targetAccount = null;
  let maxReels = DEFAULT_MAX_REELS;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--account" && args[i + 1]) targetAccount = args[++i];
    if (args[i] === "--max-reels" && args[i + 1]) maxReels = parseInt(args[++i], 10);
  }

  const accounts = targetAccount ? [targetAccount] : ACCOUNTS;

  // Validate account names
  for (const acct of accounts) {
    if (!ACCOUNTS.includes(acct)) {
      console.error(`Unknown account: ${acct}. Valid: ${ACCOUNTS.join(", ")}`);
      process.exit(1);
    }
  }

  // Ensure output dir exists
  mkdirSync(OUTPUT_DIR, { recursive: true });

  console.log("🔌 Connecting to Chrome CDP...");
  await connectCDP();
  console.log("✅ Connected\n");

  const today = todayStr();

  for (const account of accounts) {
    try {
      const reels = await scrapeAccount(account, maxReels);
      const outPath = join(OUTPUT_DIR, `${account}_${today}.json`);
      writeFileSync(outPath, JSON.stringify(reels, null, 2));
      console.log(`  ✅ Saved ${reels.length} reels → ${outPath}\n`);
    } catch (err) {
      console.error(`  ❌ Failed to scrape @${account}: ${err.message}\n`);
    }
  }

  ws.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
