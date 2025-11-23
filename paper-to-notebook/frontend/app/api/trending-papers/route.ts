import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export const revalidate = 0

// In-memory cache keyed by period
const _cache = new Map<string, { papers: any[]; ts: number }>()
const CACHE_TTL = 15 * 60 * 1000 // 15 minutes

type Period = 'day' | 'week' | 'month'

interface PaperEntry {
  id: string
  title: string
  abstract: string
  authors: string
  publishedAt: string
  upvotes: number
  githubUrl: string
  githubStars: number
  keywords: string[]
  arxivUrl: string
  hfUrl: string
  thumbnail: string
}

function decodeHtmlEntities(str: string): string {
  return str
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
}

function formatAuthors(authors: any[]): string {
  const names: string[] = (authors || []).map((a: any) => a.name).filter(Boolean)
  if (names.length > 3) return names.slice(0, 3).join(', ') + ' et al.'
  return names.join(', ')
}

function mapItem(item: any): PaperEntry | null {
  const paper = item?.paper
  if (!paper?.id || !paper?.title) return null
  return {
    id: paper.id,
    title: paper.title,
    abstract: paper.summary || item.summary || '',
    authors: formatAuthors(paper.authors || []),
    publishedAt: (paper.publishedAt || item.publishedAt || '').slice(0, 10),
    upvotes: paper.upvotes || 0,
    githubUrl: paper.githubRepo || '',
    githubStars: paper.githubStars || 0,
    keywords: (paper.ai_keywords || []).slice(0, 3) as string[],
    arxivUrl: `https://arxiv.org/abs/${paper.id}`,
    hfUrl: `https://huggingface.co/papers/${paper.id}`,
    thumbnail: item.thumbnail || '',
  }
}

// Fetch a single day from HF daily_papers API
async function fetchDay(date: string): Promise<any[]> {
  try {
    const res = await fetch(`https://huggingface.co/api/daily_papers?date=${date}`, {
      headers: { 'Accept': 'application/json', 'User-Agent': 'paper2notebook/1.0' },
    })
    if (!res.ok) return []
    return await res.json()
  } catch {
    return []
  }
}

// Scrape HF trending HTML for today (has best quality data + GitHub stars)
async function scrapeTodayTrending(): Promise<any[]> {
  try {
    const res = await fetch('https://huggingface.co/papers/trending', {
      headers: {
        'Accept': 'text/html,application/xhtml+xml',
        'User-Agent': 'Mozilla/5.0 (compatible; paper2notebook/1.0)',
      },
    })
    if (!res.ok) return []
    const html = await res.text()
    const match = html.match(/data-target="DailyPapers"\s+data-props="([^"]*)"/)
    if (!match) return []
    const props = JSON.parse(decodeHtmlEntities(match[1]))
    return props.dailyPapers || []
  } catch {
    return []
  }
}

// Aggregate multiple days, deduplicate, sort by githubStars then upvotes
function aggregateAndSort(items: any[]): PaperEntry[] {
  const paperMap = new Map<string, PaperEntry>()
  for (const item of items) {
    const entry = mapItem(item)
    if (!entry) continue
    const existing = paperMap.get(entry.id)
    // Keep the version with highest githubStars
    if (!existing || entry.githubStars > existing.githubStars) {
      paperMap.set(entry.id, entry)
    }
  }
  return Array.from(paperMap.values())
    .sort((a, b) => b.githubStars - a.githubStars || b.upvotes - a.upvotes)
}

function getPastDates(days: number): string[] {
  const dates: string[] = []
  for (let i = 0; i < days; i++) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    dates.push(d.toISOString().slice(0, 10))
  }
  return dates
}

async function fetchTrendingForPeriod(period: Period): Promise<PaperEntry[]> {
  if (period === 'day') {
    // Try HTML scrape first (richer data), fall back to daily API
    let items = await scrapeTodayTrending()
    if (items.length === 0) {
      const today = new Date().toISOString().slice(0, 10)
      items = await fetchDay(today)
    }
    return aggregateAndSort(items)
  }

  if (period === 'week') {
    // Last 7 days
    const dates = getPastDates(7)
    const results = await Promise.all(dates.map(fetchDay))
    return aggregateAndSort(results.flat())
  }

  // month — last 30 days
  const dates = getPastDates(30)
  // Fetch in batches of 10 to avoid hammering the API
  const allItems: any[] = []
  for (let i = 0; i < dates.length; i += 10) {
    const batch = dates.slice(i, i + 10)
    const results = await Promise.all(batch.map(fetchDay))
    allItems.push(...results.flat())
  }
  return aggregateAndSort(allItems)
}

export async function GET(request: NextRequest) {
  const period = (request.nextUrl.searchParams.get('period') || 'day') as Period

  // Serve from cache if fresh
  const cached = _cache.get(period)
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return NextResponse.json({ papers: cached.papers })
  }

  try {
    const papers = await fetchTrendingForPeriod(period)
    _cache.set(period, { papers, ts: Date.now() })
    return NextResponse.json({ papers })
  } catch (err) {
    console.error('Trending papers error:', err)
    // Stale cache fallback
    const stale = _cache.get(period)
    if (stale) return NextResponse.json({ papers: stale.papers })
    return NextResponse.json({ papers: [], error: true })
  }
}
