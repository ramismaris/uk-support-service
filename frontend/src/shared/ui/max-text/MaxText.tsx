import { Fragment, type ReactNode } from 'react'
import { parseMaxMarkdown, type InlineNode, type StyleType } from '@/shared/lib/max-markdown'

const styleClass: Record<StyleType, string> = {
  bold: 'font-semibold',
  italic: 'italic',
  strike: 'line-through',
  underline: 'underline underline-offset-2',
  mark: 'rounded-sm bg-attention/30 px-0.5',
}

function renderInline(nodes: InlineNode[]): ReactNode {
  return nodes.map((node, index) => {
    switch (node.type) {
      case 'text':
        return <Fragment key={index}>{node.text}</Fragment>
      case 'code':
        return (
          <code key={index} className="rounded bg-black/10 px-1 font-mono text-[0.9em]">
            {node.text}
          </code>
        )
      case 'link':
        return (
          <a
            key={index}
            href={node.href}
            target="_blank"
            rel="noreferrer"
            className="underline underline-offset-2"
          >
            {renderInline(node.children)}
          </a>
        )
      default:
        return (
          <span key={index} className={styleClass[node.type]}>
            {renderInline(node.children)}
          </span>
        )
    }
  })
}

// Text written with Max markdown, shown the way the resident sees it in the bot.
export function MaxText({ text, className = '' }: { text: string; className?: string }) {
  return (
    <div className={`break-words ${className}`}>
      {parseMaxMarkdown(text).map((block, index) => {
        if (block.type === 'heading') {
          return (
            <div key={index} className="text-[1.1em] font-semibold">
              {renderInline(block.children)}
            </div>
          )
        }
        if (block.type === 'quote') {
          return (
            <div key={index} className="border-l border-current/40 pl-2 opacity-85">
              {renderInline(block.children)}
            </div>
          )
        }
        // An empty line keeps its height, as in the bot.
        return (
          <div key={index} className="min-h-[1lh]">
            {renderInline(block.children)}
          </div>
        )
      })}
    </div>
  )
}
