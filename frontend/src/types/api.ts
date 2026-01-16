/**
 * API Request/Response Schemas
 * Auto-generated from Python backend models
 */
import { z } from "zod";

// ============== Enums ==============

export enum DocumentType {
    MARKDOWN = "markdown",
    TEXT = "text",
    PDF = "pdf",
    DOCX = "docx",
    HTML = "html",
}

export enum DocumentStatus {
    PENDING = "pending",
    PROCESSING = "processing",
    INDEXED = "indexed",
    FAILED = "failed",
}

// ============== Document Schemas ==============

/** Request schema for creating a document */
export const DocumentCreateSchema = z.object({
    title: z.string().min(1).max(500),
    content: z.string().min(1),
    doc_type: z.nativeEnum(DocumentType).default(DocumentType.MARKDOWN),
    tags: z.array(z.string()).optional(),
    auto_index: z.boolean().default(true),
});
export type DocumentCreate = z.infer<typeof DocumentCreateSchema>;

/** Request schema for updating a document */
export const DocumentUpdateSchema = z.object({
    title: z.string().min(1).max(500).optional(),
    content: z.string().min(1).optional(),
    tags: z.array(z.string()).optional(),
    reindex: z.boolean().default(true),
});
export type DocumentUpdate = z.infer<typeof DocumentUpdateSchema>;

/** Response schema for a document */
export const DocumentResponseSchema = z.object({
    id: z.string(),
    title: z.string(),
    content: z.string(),
    doc_type: z.nativeEnum(DocumentType),
    status: z.nativeEnum(DocumentStatus),
    file_path: z.string().nullable().optional(),
    file_size: z.number().default(0),
    word_count: z.number().default(0),
    outgoing_links: z.array(z.string()).default([]),
    incoming_links: z.array(z.string()).default([]),
    tags: z.array(z.string()).default([]),
    summary: z.string().nullable().optional(),
    created_at: z.string(), // datetime strings
    updated_at: z.string(),
    indexed_at: z.string().nullable().optional(),
});
export type DocumentResponse = z.infer<typeof DocumentResponseSchema>;

/** Response schema for document list */
export const DocumentListResponseSchema = z.object({
    documents: z.array(DocumentResponseSchema),
    total: z.number(),
    skip: z.number(),
    limit: z.number(),
});
export type DocumentListResponse = z.infer<typeof DocumentListResponseSchema>;

/** Response schema for linked documents */
export const LinkedDocumentsResponseSchema = z.object({
    outgoing: z.array(DocumentResponseSchema),
    incoming: z.array(DocumentResponseSchema),
});
export type LinkedDocumentsResponse = z.infer<typeof LinkedDocumentsResponseSchema>;

// ============== Chat Schemas ==============

/** Request schema for creating a conversation */
export const ConversationCreateSchema = z.object({
    title: z.string().optional().nullable(),
});
export type ConversationCreate = z.infer<typeof ConversationCreateSchema>;

/** Response schema for a conversation */
export const ConversationResponseSchema = z.object({
    id: z.string(),
    title: z.string().nullable().optional(),
    created_at: z.string(),
    updated_at: z.string(),
});
export type ConversationResponse = z.infer<typeof ConversationResponseSchema>;

/** Response schema for conversation list */
export const ConversationListResponseSchema = z.object({
    conversations: z.array(ConversationResponseSchema),
    total: z.number(),
});
export type ConversationListResponse = z.infer<typeof ConversationListResponseSchema>;

/** Response schema for a message */
export const MessageResponseSchema = z.object({
    id: z.string(),
    conversation_id: z.string(),
    role: z.string(), // 'user' | 'assistant' | 'system'
    content: z.string(),
    retrieved_chunks: z.array(z.string()).default([]),
    model_used: z.string().nullable().optional(),
    tokens_used: z.number().default(0),
    created_at: z.string(),
});
export type MessageResponse = z.infer<typeof MessageResponseSchema>;

/** Request schema for chat */
export const ChatRequestSchema = z.object({
    message: z.string().min(1),
    use_rag: z.boolean().default(true),
    model: z.string().optional().nullable(),
    stream: z.boolean().default(false),
});
export type ChatRequest = z.infer<typeof ChatRequestSchema>;

/** Response schema for chat (non-streaming) */
export const ChatResponseSchema = z.object({
    message: MessageResponseSchema,
    context_used: z.array(z.record(z.string(), z.any())).default([]),
});
export type ChatResponse = z.infer<typeof ChatResponseSchema>;

// ============== Search Schemas ==============

/** Request schema for semantic search */
export const SearchRequestSchema = z.object({
    query: z.string().min(1),
    top_k: z.number().min(1).max(50).default(10),
    include_documents: z.boolean().default(true),
});
export type SearchRequest = z.infer<typeof SearchRequestSchema>;

/** Single search result */
export const SearchResultSchema = z.object({
    id: z.string(),
    content: z.string(),
    score: z.number(),
    metadata: z.record(z.string(), z.any()).default({}),
    document: z.record(z.string(), z.any()).nullable().optional(),
});
export type SearchResult = z.infer<typeof SearchResultSchema>;

/** Response schema for search */
export const SearchResponseSchema = z.object({
    query: z.string(),
    results: z.array(SearchResultSchema),
    total: z.number(),
});
export type SearchResponse = z.infer<typeof SearchResponseSchema>;

// ============== Tag Schemas ==============

/** Response schema for a tag */
export const TagResponseSchema = z.object({
    id: z.string(),
    name: z.string(),
    color: z.string(),
    document_count: z.number(),
});
export type TagResponse = z.infer<typeof TagResponseSchema>;

/** Response schema for tag list */
export const TagListResponseSchema = z.object({
    tags: z.array(TagResponseSchema),
});
export type TagListResponse = z.infer<typeof TagListResponseSchema>;

// ============== Stats Schemas ==============

/** Response schema for system stats */
export const StatsResponseSchema = z.object({
    total_documents: z.number(),
    total_chunks: z.number(),
    total_tags: z.number(),
    top_tags: z.array(z.record(z.string(), z.any())),
});
export type StatsResponse = z.infer<typeof StatsResponseSchema>;

// ============== Health Schemas ==============

/** Response schema for health check */
export const HealthResponseSchema = z.object({
    status: z.string(),
    version: z.string(),
    database: z.string(),
    vector_store: z.record(z.string(), z.any()),
    llm: z.record(z.string(), z.any()),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

// ============== Error Schemas ==============

/** Error response schema */
export const ErrorResponseSchema = z.object({
    detail: z.string(),
    code: z.string().nullable().optional(),
});
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;
