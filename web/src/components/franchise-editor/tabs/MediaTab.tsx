'use client'

import type { Franchise } from '@/src/schemas/franchises/Franchise'
import MediaLogoCard from '../media/MediaLogoCard'
import MediaThumbnailCard from '../media/MediaThumbnailCard'
import MediaGalleryManager from '../media/MediaGalleryManager'
import MediaVideoList from '../media/MediaVideoList'

interface MediaTabProps {
  franchise: Franchise
  token: string
}

export default function MediaTab({ franchise, token }: MediaTabProps) {
  return (
    <div className="space-y-10">
      <MediaLogoCard
        franchiseId={franchise.id}
        currentUrl={franchise.logoUrl}
        token={token}
      />

      <div className="border-t border-border/40" />

      <MediaThumbnailCard
        franchiseId={franchise.id}
        currentUrl={franchise.thumbnailUrl}
        token={token}
      />

      <div className="border-t border-border/40" />

      <MediaGalleryManager
        franchiseId={franchise.id}
        galleryUrls={franchise.galleryUrls}
        token={token}
      />

      <div className="border-t border-border/40" />

      <MediaVideoList
        franchiseId={franchise.id}
        videoUrl={franchise.videoUrl}
        token={token}
      />
    </div>
  )
}
