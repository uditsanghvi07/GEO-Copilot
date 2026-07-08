import type { PipelineStepKey } from './pipelineSteps'

export const GENERAL_GEO_TIPS = [
  'GEO optimizes how ChatGPT, Claude, and Gemini discover your product.',
  'AI systems recommend products they can clearly understand — not just rank in search.',
  'Rich FAQ pages help generative AI answer user questions about your app.',
  'Schema.org markup tells AI crawlers what your product actually is.',
  'Fresh Play Store listings signal an actively maintained product to AI models.',
  'Review sentiment shapes how AI summarizes your strengths and weaknesses.',
  'RAG-grounded content keeps AI-generated copy factual and on-brand.',
  'Competitor GEO gaps reveal quick wins for discoverability improvements.',
] as const

export const STAGE_GEO_TIPS: Record<PipelineStepKey, readonly string[]> = {
  website_crawler: [
    'Crawling your site — AI reads titles, meta descriptions, and page structure first.',
    'GEO tip: Add clear H1/H2 headings so AI can map your product features.',
    'Internal links help AI crawlers traverse your full content graph.',
  ],
  play_store_analyzer: [
    'Analyzing Play Store — listing quality directly affects AI app recommendations.',
    'GEO tip: A detailed app description gives AI more context to cite you.',
    'Install counts and ratings are authority signals for generative engines.',
  ],
  review_intelligence: [
    'Map-reducing reviews — extracting themes AI would surface to users.',
    'GEO tip: Address top complaints publicly — AI notices resolved pain points.',
    'Positive review themes become talking points for AI recommendations.',
  ],
  audit: [
    'Computing your GEO score — 7 weighted dimensions of AI discoverability.',
    'GEO tip: Documentation depth is worth up to 20 points on your score.',
    'Structured data and FAQ presence are high-impact quick wins.',
  ],
  competitor: [
    'Benchmarking competitors — finding what AI sees that you are missing.',
    'GEO tip: If competitors have FAQs you lack, AI may prefer them in answers.',
    'GEO scores compare discoverability, not just marketing spend.',
  ],
  content_faq: [
    'Generating RAG-grounded FAQ — content rooted in your real product data.',
    'GEO tip: Publish AI-optimized FAQs on your site for crawler ingestion.',
    'Grounded content reduces hallucination risk in AI-generated answers.',
  ],
  reporting: [
    'Assembling your audit report — actionable GEO improvements in one view.',
    'GEO tip: Re-run audits monthly as AI ranking signals evolve quickly.',
    'Your action plan prioritizes fixes by estimated GEO score impact.',
  ],
}

export function tipsForStage(stageKey: PipelineStepKey | null): string[] {
  const stageTips = stageKey ? [...STAGE_GEO_TIPS[stageKey]] : []
  return [...stageTips, ...GENERAL_GEO_TIPS]
}
