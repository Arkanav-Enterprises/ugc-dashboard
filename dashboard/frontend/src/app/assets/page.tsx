"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  getReferenceImages,
  getClips,
  getAssetUsage,
  assetUrl,
  type AssetInfo,
  type AssetUsageRow,
} from "@/lib/api";

const PERSONA_COLORS: Record<string, string> = {
  aliyah: "#8b5cf6",
  riley: "#10b981",
  sanya: "#ef4444",
  emilly: "#3b82f6",
};

export default function AssetManagerPage() {
  const [images, setImages] = useState<AssetInfo[]>([]);
  const [clips, setClips] = useState<AssetInfo[]>([]);
  const [usage, setUsage] = useState<AssetUsageRow[]>([]);

  useEffect(() => {
    getReferenceImages().then(setImages);
    getClips().then(setClips);
    getAssetUsage().then(setUsage);
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Asset Manager</h2>

      <Tabs defaultValue="images">
        <TabsList>
          <TabsTrigger value="images">
            Reference Images ({images.length})
          </TabsTrigger>
          <TabsTrigger value="clips">
            Generated Clips ({clips.length})
          </TabsTrigger>
          <TabsTrigger value="usage">
            Usage History ({usage.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="images" className="mt-4">
          <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {images.map((img) => (
              <Card key={img.name}>
                <CardContent className="pt-3 space-y-2">
                  <div className="aspect-[9/16] bg-muted rounded-md overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={assetUrl(img.path)}
                      alt={img.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="flex items-center gap-1">
                    {img.persona && (
                      <Badge
                        variant="outline"
                        className="text-xs"
                        style={{
                          borderColor: PERSONA_COLORS[img.persona],
                          color: PERSONA_COLORS[img.persona],
                        }}
                      >
                        {img.persona}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground truncate">
                    {img.name}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="clips" className="mt-4">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {clips.map((clip) => (
              <Card key={clip.path}>
                <CardContent className="pt-3 space-y-2">
                  <video
                    src={assetUrl(clip.path)}
                    className="w-full aspect-[9/16] object-cover rounded-md bg-black"
                    controls
                    muted
                    preload="metadata"
                  />
                  <div className="flex items-center gap-1">
                    {clip.persona && (
                      <Badge
                        variant="outline"
                        className="text-xs"
                        style={{
                          borderColor: PERSONA_COLORS[clip.persona],
                          color: PERSONA_COLORS[clip.persona],
                        }}
                      >
                        {clip.persona}
                      </Badge>
                    )}
                    {clip.type && (
                      <Badge variant="secondary" className="text-xs">
                        {clip.type}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground truncate">
                    {clip.name}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="usage" className="mt-4">
          <Card>
            <CardContent className="pt-4">
              {usage.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No usage history yet
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-2 pr-4 font-medium">Date</th>
                        <th className="pb-2 pr-4 font-medium">Account</th>
                        <th className="pb-2 pr-4 font-medium">Hook Clip</th>
                        <th className="pb-2 pr-4 font-medium">Reaction Clip</th>
                        <th className="pb-2 font-medium">Screen Rec</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usage.map((row, i) => {
                        const persona = row.account.split(".")[0];
                        return (
                          <tr key={i} className="border-b last:border-0">
                            <td className="py-2 pr-4">{row.date}</td>
                            <td className="py-2 pr-4">
                              <Badge
                                variant="outline"
                                style={{
                                  borderColor: PERSONA_COLORS[persona],
                                  color: PERSONA_COLORS[persona],
                                }}
                              >
                                {row.account}
                              </Badge>
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground">
                              {row.hook_clip}
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground">
                              {row.reaction_clip}
                            </td>
                            <td className="py-2 text-muted-foreground">
                              {row.screen_recording}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
