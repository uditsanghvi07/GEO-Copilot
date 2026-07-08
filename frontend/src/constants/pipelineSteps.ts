export const PIPELINE_STEPS = [
  { key: 'website_crawler', label: 'Crawling website' },
  { key: 'play_store_analyzer', label: 'Analyzing Play Store' },
  { key: 'review_intelligence', label: 'Analyzing reviews' },
  { key: 'audit', label: 'Scoring GEO discoverability' },
  { key: 'competitor', label: 'Comparing competitors' },
  {
    key: 'content_faq',
    label: 'Generating content',
    relatedKeys: ['content_meta_description'] as const,
  },
  { key: 'reporting', label: 'Building report' },
] as const

export type PipelineStepKey = (typeof PIPELINE_STEPS)[number]['key']
