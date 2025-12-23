"""
Repository Implementations
Concrete implementations of repository interfaces using SQLAlchemy
"""
from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy import select, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.document import (
    Document, DocumentType, DocumentStatus,
    DocumentChunk, Conversation, Message, Tag, User
)
from src.domain.repositories.interfaces import (
    DocumentRepository, ChunkRepository, ConversationRepository,
    MessageRepository, TagRepository, UserRepository
)
from src.infrastructure.database.models import (
    DocumentModel, DocumentChunkModel, ConversationModel,
    MessageModel, TagModel, UserModel,
    DocumentTypeEnum, DocumentStatusEnum
)


class SQLAlchemyDocumentRepository(DocumentRepository):
    """SQLAlchemy implementation of DocumentRepository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_entity(self, model: DocumentModel) -> Document:
        """Convert ORM model to domain entity"""
        return Document(
            id=model.id,
            title=model.title,
            content=model.content,
            doc_type=DocumentType(model.doc_type.value),
            status=DocumentStatus(model.status.value),
            file_path=model.file_path,
            file_size=model.file_size,
            word_count=model.word_count,
            outgoing_links=model.outgoing_links or [],
            incoming_links=model.incoming_links or [],
            tags=model.tags or [],
            summary=model.summary,
            created_at=model.created_at,
            updated_at=model.updated_at,
            indexed_at=model.indexed_at,
            user_id=model.user_id,
        )
    
    def _to_model(self, entity: Document) -> DocumentModel:
        """Convert domain entity to ORM model"""
        return DocumentModel(
            id=entity.id,
            title=entity.title,
            content=entity.content,
            doc_type=DocumentTypeEnum(entity.doc_type.value),
            status=DocumentStatusEnum(entity.status.value),
            file_path=entity.file_path,
            file_size=entity.file_size,
            word_count=entity.word_count,
            outgoing_links=entity.outgoing_links,
            incoming_links=entity.incoming_links,
            tags=entity.tags,
            summary=entity.summary,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            indexed_at=entity.indexed_at,
            user_id=entity.user_id,
        )
    
    async def create(self, document: Document) -> Document:
        model = self._to_model(document)
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_id(self, doc_id: str) -> Optional[Document]:
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.id == doc_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_title(self, title: str) -> Optional[Document]:
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.title == title)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_all(
        self, 
        user_id: Optional[str] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Document]:
        query = select(DocumentModel).offset(skip).limit(limit)
        if user_id:
            query = query.where(DocumentModel.user_id == user_id)
        query = query.order_by(DocumentModel.updated_at.desc())
        
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def update(self, document: Document) -> Document:
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.id == document.id)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Document {document.id} not found")
        
        model.title = document.title
        model.content = document.content
        model.doc_type = DocumentTypeEnum(document.doc_type.value)
        model.status = DocumentStatusEnum(document.status.value)
        model.file_path = document.file_path
        model.file_size = document.file_size
        model.word_count = document.word_count
        model.outgoing_links = document.outgoing_links
        model.incoming_links = document.incoming_links
        model.tags = document.tags
        model.summary = document.summary
        model.updated_at = datetime.utcnow()
        model.indexed_at = document.indexed_at
        
        await self.session.flush()
        return self._to_entity(model)
    
    async def delete(self, doc_id: str) -> bool:
        result = await self.session.execute(
            delete(DocumentModel).where(DocumentModel.id == doc_id)
        )
        return result.rowcount > 0
    
    async def search_by_title(self, query: str, limit: int = 10) -> List[Document]:
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.title.ilike(f"%{query}%"))
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def get_by_tag(self, tag: str, limit: int = 100) -> List[Document]:
        # SQLite JSON query - for production consider PostgreSQL with proper JSON support
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.tags.contains([tag]))
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def get_linked_documents(self, doc_id: str) -> Dict[str, List[Document]]:
        doc = await self.get_by_id(doc_id)
        if not doc:
            return {"outgoing": [], "incoming": []}
        
        outgoing = []
        incoming = []
        
        for link_id in doc.outgoing_links:
            linked = await self.get_by_id(link_id)
            if linked:
                outgoing.append(linked)
        
        for link_id in doc.incoming_links:
            linked = await self.get_by_id(link_id)
            if linked:
                incoming.append(linked)
        
        return {"outgoing": outgoing, "incoming": incoming}
    
    async def count(self, user_id: Optional[str] = None) -> int:
        query = select(func.count(DocumentModel.id))
        if user_id:
            query = query.where(DocumentModel.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar() or 0


class SQLAlchemyChunkRepository(ChunkRepository):
    """SQLAlchemy implementation of ChunkRepository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_entity(self, model: DocumentChunkModel) -> DocumentChunk:
        return DocumentChunk(
            id=model.id,
            document_id=model.document_id,
            content=model.content,
            chunk_index=model.chunk_index,
            start_char=model.start_char,
            end_char=model.end_char,
            parent_chunk_id=model.parent_chunk_id,
            created_at=model.created_at,
        )
    
    def _to_model(self, entity: DocumentChunk) -> DocumentChunkModel:
        return DocumentChunkModel(
            id=entity.id,
            document_id=entity.document_id,
            content=entity.content,
            chunk_index=entity.chunk_index,
            start_char=entity.start_char,
            end_char=entity.end_char,
            parent_chunk_id=entity.parent_chunk_id,
            created_at=entity.created_at,
        )
    
    async def create_many(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        models = [self._to_model(c) for c in chunks]
        self.session.add_all(models)
        await self.session.flush()
        return [self._to_entity(m) for m in models]
    
    async def get_by_document(self, doc_id: str) -> List[DocumentChunk]:
        result = await self.session.execute(
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id == doc_id)
            .order_by(DocumentChunkModel.chunk_index)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def delete_by_document(self, doc_id: str) -> int:
        result = await self.session.execute(
            delete(DocumentChunkModel).where(DocumentChunkModel.document_id == doc_id)
        )
        return result.rowcount


class SQLAlchemyConversationRepository(ConversationRepository):
    """SQLAlchemy implementation of ConversationRepository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_entity(self, model: ConversationModel) -> Conversation:
        return Conversation(
            id=model.id,
            title=model.title,
            user_id=model.user_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def create(self, conversation: Conversation) -> Conversation:
        model = ConversationModel(
            id=conversation.id,
            title=conversation.title,
            user_id=conversation.user_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_id(self, conv_id: str) -> Optional[Conversation]:
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.id == conv_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_all(
        self, 
        user_id: Optional[str] = None,
        skip: int = 0, 
        limit: int = 50
    ) -> List[Conversation]:
        query = select(ConversationModel).offset(skip).limit(limit)
        if user_id:
            query = query.where(ConversationModel.user_id == user_id)
        query = query.order_by(ConversationModel.updated_at.desc())
        
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def delete(self, conv_id: str) -> bool:
        result = await self.session.execute(
            delete(ConversationModel).where(ConversationModel.id == conv_id)
        )
        return result.rowcount > 0


class SQLAlchemyMessageRepository(MessageRepository):
    """SQLAlchemy implementation of MessageRepository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_entity(self, model: MessageModel) -> Message:
        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            role=model.role,
            content=model.content,
            retrieved_chunks=model.retrieved_chunks or [],
            model_used=model.model_used,
            tokens_used=model.tokens_used,
            created_at=model.created_at,
        )
    
    async def create(self, message: Message) -> Message:
        model = MessageModel(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            retrieved_chunks=message.retrieved_chunks,
            model_used=message.model_used,
            tokens_used=message.tokens_used,
            created_at=message.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_conversation(
        self, 
        conv_id: str,
        limit: int = 50
    ) -> List[Message]:
        result = await self.session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == conv_id)
            .order_by(MessageModel.created_at.asc())
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def delete_by_conversation(self, conv_id: str) -> int:
        result = await self.session.execute(
            delete(MessageModel).where(MessageModel.conversation_id == conv_id)
        )
        return result.rowcount


class SQLAlchemyTagRepository(TagRepository):
    """SQLAlchemy implementation of TagRepository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_entity(self, model: TagModel) -> Tag:
        return Tag(
            id=model.id,
            name=model.name,
            color=model.color,
            document_count=model.document_count,
            created_at=model.created_at,
        )
    
    async def create(self, tag: Tag) -> Tag:
        model = TagModel(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            document_count=tag.document_count,
            created_at=tag.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_name(self, name: str) -> Optional[Tag]:
        result = await self.session.execute(
            select(TagModel).where(TagModel.name == name.lower())
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_all(self) -> List[Tag]:
        result = await self.session.execute(
            select(TagModel).order_by(TagModel.name)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def get_popular(self, limit: int = 20) -> List[Tag]:
        result = await self.session.execute(
            select(TagModel)
            .order_by(TagModel.document_count.desc())
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def update_count(self, name: str, delta: int) -> None:
        result = await self.session.execute(
            select(TagModel).where(TagModel.name == name.lower())
        )
        model = result.scalar_one_or_none()
        if model:
            model.document_count = max(0, model.document_count + delta)
            await self.session.flush()


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            username=model.username,
            email=model.email,
            hashed_password=model.hashed_password,
            is_active=model.is_active,
            is_admin=model.is_admin,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def create(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def update(self, user: User) -> User:
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user.id)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"User {user.id} not found")
        
        model.username = user.username
        model.email = user.email
        model.hashed_password = user.hashed_password
        model.is_active = user.is_active
        model.is_admin = user.is_admin
        model.updated_at = datetime.utcnow()
        
        await self.session.flush()
        return self._to_entity(model)
