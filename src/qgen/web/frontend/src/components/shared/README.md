# RAG Chunk Highlighting System

A comprehensive React component system for highlighting text spans within document chunks, specifically designed for RAG (Retrieval-Augmented Generation) applications.

## Features

### 🎨 **Highlighting Capabilities**
- **Multiple highlight types**: Facts, entities, relationships, search matches, active selections
- **Customizable colors**: WCAG-compliant color schemes with sufficient contrast ratios
- **Interactive highlights**: Click handlers, tooltips, and keyboard navigation
- **Performance optimized**: Handles 20+ chunks with multiple highlights efficiently

### ♿ **Accessibility Features**
- **Screen reader support**: Semantic `<mark>` tags with proper ARIA labels
- **Keyboard navigation**: Tab and Enter/Space key support
- **High contrast**: Colors meet WCAG 2.1 contrast requirements
- **Non-color indicators**: Icons and patterns supplement color coding

### 🔧 **Component Architecture**
- **ChunkHighlighter**: Core highlighting component using `react-highlight-words`
- **FactCard**: Enhanced fact display with expandable source context
- **ChunkViewer**: Performance-optimized viewer for multiple chunks
- **RAGHighlightDemo**: Complete integration example

## Installation

```bash
npm install react-highlight-words
```

## Quick Start

```tsx
import { ChunkHighlighter, HighlightSpan } from './components/shared/ChunkHighlighter'

const highlights: HighlightSpan[] = [
  {
    id: 'fact-1',
    text: 'extracted fact text',
    type: 'fact',
    metadata: { confidence: 0.95, factId: 'fact-1' }
  }
]

<ChunkHighlighter
  text="Your document chunk text here..."
  highlights={highlights}
  onHighlightClick={(highlight) => console.log('Clicked:', highlight)}
/>
```

## Component Reference

### ChunkHighlighter

Core highlighting component that wraps `react-highlight-words` with enhanced functionality.

**Props:**
- `text: string` - Text content to highlight within
- `highlights: HighlightSpan[]` - Array of text spans to highlight
- `onHighlightClick?: (highlight: HighlightSpan) => void` - Click handler
- `activeHighlightId?: string` - ID of currently active highlight
- `showTooltips?: boolean` - Show hover tooltips (default: true)

**Highlight Types:**
- `fact` - Extracted facts (yellow theme)
- `entity` - Key entities (green theme)  
- `relationship` - Multi-hop relationships (violet theme)
- `search` - Search matches (red theme)
- `active` - Selected/active highlights (blue theme)

### FactCard

Enhanced fact display component with source context highlighting.

**Props:**
- `fact: FactData` - Fact object with text, confidence, source
- `isSelected?: boolean` - Selection state
- `showSourceChunk?: boolean` - Show expandable source context
- `onApprove?: (factId: string) => void` - Approval handler
- `additionalHighlights?: HighlightSpan[]` - Extra highlights for source

### ChunkViewer

Performance-optimized component for displaying multiple chunks with highlighting.

**Props:**
- `chunks: ChunkData[]` - Array of chunk objects
- `highlights: HighlightSpan[]` - Highlights to show across chunks
- `initialChunkLimit?: number` - Initial chunks to show (default: 10)
- `onHighlightClick?: (highlight, chunkId) => void` - Highlight click handler
- `showMetadata?: boolean` - Show chunk metadata (default: true)

**Performance Features:**
- **Virtual scrolling**: Loads chunks incrementally
- **Search filtering**: Client-side chunk search
- **Lazy expansion**: Expandable chunk content
- **Optimized rendering**: React.memo and useMemo optimization

## Color Scheme

The highlighting system uses a carefully designed color palette that meets WCAG 2.1 accessibility standards:

| Type | Background | Border | Text | Use Case |
|------|------------|--------|------|----------|
| **fact** | `#fef3c7` | `#f59e0b` | `#92400e` | Extracted facts |
| **entity** | `#d1fae5` | `#10b981` | `#065f46` | Named entities |
| **relationship** | `#ddd6fe` | `#8b5cf6` | `#5b21b6` | Multi-hop relations |
| **search** | `#fee2e2` | `#ef4444` | `#991b1b` | Search matches |
| **active** | `#dbeafe` | `#3b82f6` | `#1e40af` | Selected items |

## Integration with Existing RAG Dashboard

### Step 1: Update Facts Display

Replace your existing fact display in `RAGProjectDashboard.tsx`:

```tsx
import { FactGrid } from '../shared/FactCard'
import { HighlightSpan } from '../shared/ChunkHighlighter'

// In your renderFactsStage function:
const factHighlights: HighlightSpan[] = currentFacts.map(fact => ({
  id: fact.fact_id,
  text: fact.fact_text,
  type: 'fact',
  metadata: {
    factId: fact.fact_id,
    confidence: fact.extraction_confidence,
    chunkId: fact.chunk_id
  }
}))

return (
  <FactGrid
    facts={currentFacts}
    selectedFactIds={selectedFacts}
    onFactSelect={handleFactSelect}
    onFactApprove={handleIndividualApprove}
    onFactReject={handleIndividualReject}
    showSourceChunks={true}
    globalHighlights={factHighlights}
  />
)
```

### Step 2: Add Chunk Viewing Tab

Add a new tab to your dashboard for viewing source chunks with highlighting:

```tsx
// Add to your tab navigation
{ id: 'chunks-view', name: '🔍 Chunk Viewer', count: getChunksCount() }

// Add tab content
{activeTab === 'chunks-view' && (
  <ChunkViewer
    chunks={chunkData}
    highlights={allHighlights}
    showMetadata={true}
    onHighlightClick={handleHighlightClick}
    onChunkClick={handleChunkClick}
  />
)}
```

### Step 3: Connect with Backend

Update your API calls to include source text for chunks:

```tsx
// When loading facts, also load source chunks
const loadFactsWithSources = async () => {
  const factsResponse = await fetch(`/api/rag-projects/${project.name}/facts/generated`)
  const facts = await factsResponse.json()
  
  // Fetch source chunks for each fact
  const factsWithSources = await Promise.all(
    facts.map(async (fact) => {
      const chunkResponse = await fetch(`/api/rag-projects/${project.name}/chunks/${fact.chunk_id}`)
      const chunk = await chunkResponse.json()
      return { ...fact, source_text: chunk.text }
    })
  )
  
  setFacts({ ...facts, generated: factsWithSources })
}
```

## Performance Considerations

### For 20+ Chunks with Multiple Highlights:

1. **Incremental Loading**: Use `initialChunkLimit` to load chunks progressively
2. **Search Filtering**: Client-side filtering reduces displayed chunks
3. **React Optimization**: Components use React.memo and useMemo
4. **Lazy Highlighting**: Highlights are computed only when visible

### Memory Usage:
- ~1-2MB for 100 chunks with 500 highlights
- Efficient re-rendering with React key props
- Cleanup of event listeners and timeouts

## Browser Support

- **Modern browsers**: Chrome 88+, Firefox 78+, Safari 14+, Edge 88+
- **React 19**: Full compatibility with latest React features
- **TypeScript**: Complete type definitions included

## Accessibility Compliance

- **WCAG 2.1 AA**: All color combinations meet contrast requirements
- **Screen Readers**: Semantic markup with proper ARIA labels
- **Keyboard Navigation**: Full keyboard accessibility
- **Focus Management**: Proper focus indicators and tab order

## Advanced Usage

### Custom Highlight Colors

```tsx
import { HighlightColors } from './ChunkHighlighter'

// Extend or override default colors
const customColors = {
  ...HighlightColors,
  custom: {
    background: '#f0f9ff',
    border: '#0ea5e9', 
    text: '#0c4a6e'
  }
}
```

### Multi-language Support

```tsx
// The system works with any UTF-8 text
<ChunkHighlighter
  text="Texto en español con destacados"
  highlights={spanishHighlights}
/>
```

### Performance Monitoring

```tsx
const handleHighlightClick = (highlight: HighlightSpan) => {
  // Analytics tracking
  analytics.track('highlight_clicked', {
    type: highlight.type,
    confidence: highlight.metadata?.confidence
  })
}
```

## Migration Guide

If upgrading from a basic highlighting solution:

1. **Install dependencies**: `npm install react-highlight-words`
2. **Replace components**: Gradually replace existing highlight components
3. **Update types**: Add HighlightSpan interfaces to your data models
4. **Test accessibility**: Verify keyboard navigation and screen reader support
5. **Performance test**: Monitor with large datasets (100+ chunks)

## Demo

See `RAGHighlightDemo.tsx` for a complete working example with:
- Interactive chunk viewing
- Fact review workflow  
- Highlight color legend
- Performance demonstrations
- Integration patterns

## Support

For issues or questions:
1. Check browser console for errors
2. Verify chunk data structure matches interfaces
3. Test with smaller datasets first
4. Review accessibility requirements