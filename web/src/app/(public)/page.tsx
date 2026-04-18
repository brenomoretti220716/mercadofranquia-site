'use client'

import FeaturedFranchises from '@/src/components/home/FeaturedFranchises'
import MacroIndicators from '@/src/components/home/MacroIndicators'
import TickerBar from '@/src/components/home/TickerBar'
import Header from '../../components/header/Header'
import HeroSearch from '../../components/home/hero-search/HeroSearch'
import NewsSection from '../../components/home/NewsSection'
import ReviewsSection from '../../components/home/ReviewsSection'
import SegmentsSection from '../../components/home/SegmentsSection'

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      <TickerBar />
      <main className="flex-1">
        <HeroSearch />
        <MacroIndicators />
        <FeaturedFranchises />
        <SegmentsSection />
        <ReviewsSection />
        <NewsSection />
      </main>
    </div>
  )
}
