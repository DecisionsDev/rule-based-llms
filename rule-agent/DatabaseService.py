"""
Database Service for Underwriting AI System
Manages PostgreSQL connections and provides CRUD operations for rule containers, banks, and policies.
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

Base = declarative_base()


# SQLAlchemy Models
class Bank(Base):
    __tablename__ = 'banks'

    bank_id = Column(String(50), primary_key=True)
    bank_name = Column(String(255), nullable=False)
    description = Column(Text)
    contact_email = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    containers = relationship("RuleContainer", back_populates="bank", cascade="all, delete-orphan")
    requests = relationship("RuleRequest", back_populates="bank")


class PolicyType(Base):
    __tablename__ = 'policy_types'

    policy_type_id = Column(String(50), primary_key=True)
    policy_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    containers = relationship("RuleContainer", back_populates="policy_type", cascade="all, delete-orphan")
    requests = relationship("RuleRequest", back_populates="policy_type")


class RuleContainer(Base):
    __tablename__ = 'rule_containers'

    id = Column(Integer, primary_key=True)
    container_id = Column(String(255), unique=True, nullable=False)
    bank_id = Column(String(50), ForeignKey('banks.bank_id', ondelete='CASCADE'), nullable=False)
    policy_type_id = Column(String(50), ForeignKey('policy_types.policy_type_id', ondelete='CASCADE'), nullable=False)

    # Container details
    platform = Column(String(20), nullable=False)
    container_name = Column(String(255))
    endpoint = Column(String(500), nullable=False)
    port = Column(Integer)

    # Status tracking
    status = Column(String(20), default='deploying')
    health_check_url = Column(String(500))
    last_health_check = Column(DateTime)
    health_status = Column(String(20), default='unknown')
    failure_reason = Column(Text)

    # Deployment metadata
    document_hash = Column(String(64))
    s3_policy_url = Column(String(500))
    s3_jar_url = Column(String(500))
    s3_drl_url = Column(String(500))
    s3_excel_url = Column(String(500))
    s3_test_harness_url = Column(Text)

    # Versioning
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

    # Resource usage
    cpu_limit = Column(String(20))
    memory_limit = Column(String(20))

    # Timestamps
    deployed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    stopped_at = Column(DateTime)

    # Relationships
    bank = relationship("Bank", back_populates="containers")
    policy_type = relationship("PolicyType", back_populates="containers")
    requests = relationship("RuleRequest", back_populates="container")
    deployment_history = relationship("ContainerDeploymentHistory", back_populates="container", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("platform IN ('docker', 'kubernetes', 'local')", name='check_platform'),
        CheckConstraint("status IN ('deploying', 'running', 'stopped', 'failed', 'unhealthy')", name='check_status'),
        CheckConstraint("health_status IN ('healthy', 'unhealthy', 'unknown')", name='check_health_status'),
        Index('idx_containers_bank_policy', 'bank_id', 'policy_type_id'),
        Index('idx_containers_status', 'status'),
        Index('idx_containers_health', 'health_status'),
        Index('idx_containers_platform', 'platform'),
    )


class RuleRequest(Base):
    __tablename__ = 'rule_requests'

    id = Column(Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey('rule_containers.id', ondelete='SET NULL'))
    bank_id = Column(String(50), ForeignKey('banks.bank_id', ondelete='SET NULL'))
    policy_type_id = Column(String(50), ForeignKey('policy_types.policy_type_id', ondelete='SET NULL'))

    # Request details
    request_id = Column(UUID(as_uuid=True), server_default=func.uuid_generate_v4())
    endpoint = Column(String(255))
    http_method = Column(String(10))

    # Payload
    request_payload = Column(JSONB)
    response_payload = Column(JSONB)

    # Performance
    execution_time_ms = Column(Integer)
    status_code = Column(Integer)
    status = Column(String(20))
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    container = relationship("RuleContainer", back_populates="requests")
    bank = relationship("Bank", back_populates="requests")
    policy_type = relationship("PolicyType", back_populates="requests")

    __table_args__ = (
        CheckConstraint("status IN ('success', 'error', 'timeout')", name='check_request_status'),
        Index('idx_requests_container', 'container_id'),
        Index('idx_requests_bank', 'bank_id'),
        Index('idx_requests_created_at', 'created_at'),
        Index('idx_requests_status', 'status'),
    )


class ContainerDeploymentHistory(Base):
    __tablename__ = 'container_deployment_history'

    id = Column(Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey('rule_containers.id', ondelete='CASCADE'))
    bank_id = Column(String(50))
    policy_type_id = Column(String(50))

    # Deployment details
    action = Column(String(20))
    version = Column(Integer)
    platform = Column(String(20))
    endpoint = Column(String(500))

    # Change tracking
    document_hash = Column(String(64))
    changes_description = Column(Text)
    deployed_by = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    container = relationship("RuleContainer", back_populates="deployment_history")

    __table_args__ = (
        CheckConstraint("action IN ('deployed', 'updated', 'stopped', 'restarted', 'failed')", name='check_action'),
        Index('idx_history_container', 'container_id'),
        Index('idx_history_created_at', 'created_at'),
    )


class ExtractedRule(Base):
    __tablename__ = 'extracted_rules'

    id = Column(Integer, primary_key=True)
    bank_id = Column(String(50), ForeignKey('banks.bank_id', ondelete='CASCADE'), nullable=False)
    policy_type_id = Column(String(50), ForeignKey('policy_types.policy_type_id', ondelete='CASCADE'), nullable=False)

    # Rule details
    rule_name = Column(String(255), nullable=False)
    requirement = Column(Text, nullable=False)
    category = Column(String(100))
    source_document = Column(String(500))

    # Source location tracking
    page_number = Column(Integer)
    clause_reference = Column(String(100))

    # Metadata
    document_hash = Column(String(64))
    extraction_timestamp = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bank = relationship("Bank")
    policy_type = relationship("PolicyType")

    __table_args__ = (
        Index('idx_extracted_rules_bank_policy', 'bank_id', 'policy_type_id'),
        Index('idx_extracted_rules_active', 'is_active'),
        Index('idx_extracted_rules_created_at', 'created_at'),
        Index('idx_extracted_rules_page', 'page_number'),
        Index('idx_extracted_rules_clause', 'clause_reference'),
    )


class PolicyExtractionQuery(Base):
    __tablename__ = 'policy_extraction_queries'

    id = Column(Integer, primary_key=True)
    bank_id = Column(String(50), ForeignKey('banks.bank_id', ondelete='CASCADE'), nullable=False)
    policy_type_id = Column(String(50), ForeignKey('policy_types.policy_type_id', ondelete='CASCADE'), nullable=False)

    # Query and response details
    query_text = Column(Text, nullable=False)
    response_text = Column(Text)
    confidence_score = Column(Integer)  # Textract confidence score (0-100)

    # Source location tracking
    page_number = Column(Integer)
    clause_reference = Column(String(100))

    # Metadata
    document_hash = Column(String(64), nullable=False)
    source_document = Column(String(500))
    extraction_method = Column(String(50), default='textract')
    query_order = Column(Integer)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bank = relationship("Bank")
    policy_type = relationship("PolicyType")

    __table_args__ = (
        Index('idx_extraction_queries_bank_policy', 'bank_id', 'policy_type_id'),
        Index('idx_extraction_queries_document_hash', 'document_hash'),
        Index('idx_extraction_queries_active', 'is_active'),
        Index('idx_extraction_queries_created_at', 'created_at'),
        Index('idx_extraction_queries_page', 'page_number'),
        Index('idx_extraction_queries_clause', 'clause_reference'),
    )


class HierarchicalRule(Base):
    __tablename__ = 'hierarchical_rules'

    id = Column(Integer, primary_key=True)
    bank_id = Column(String(50), ForeignKey('banks.bank_id', ondelete='CASCADE'), nullable=False)
    policy_type_id = Column(String(50), ForeignKey('policy_types.policy_type_id', ondelete='CASCADE'), nullable=False)

    # Rule details
    rule_id = Column(String(50), nullable=False)  # e.g., "1", "5.1", "11.1.1.1.1"
    name = Column(String(255), nullable=False)
    description = Column(Text)
    expected = Column(String(255))
    actual = Column(String(255))
    confidence = Column(Float)
    passed = Column(Boolean)

    # Hierarchy
    parent_id = Column(Integer, ForeignKey('hierarchical_rules.id', ondelete='CASCADE'))
    level = Column(Integer, default=0)  # 0 for root, 1 for first level children, etc.
    order_index = Column(Integer, default=0)  # For maintaining order within same parent

    # Source location tracking
    page_number = Column(Integer)
    clause_reference = Column(String(100))

    # Metadata
    document_hash = Column(String(64))
    source_document = Column(String(500))
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bank = relationship("Bank")
    policy_type = relationship("PolicyType")
    parent = relationship("HierarchicalRule", remote_side=[id], backref="children")

    __table_args__ = (
        Index('idx_hierarchical_rules_bank_policy', 'bank_id', 'policy_type_id'),
        Index('idx_hierarchical_rules_parent', 'parent_id'),
        Index('idx_hierarchical_rules_active', 'is_active'),
        Index('idx_hierarchical_rules_hash', 'document_hash'),
        Index('idx_hierarchical_rules_level', 'level'),
        Index('idx_hierarchical_rules_page', 'page_number'),
        Index('idx_hierarchical_rules_clause', 'clause_reference'),
    )


class TestCase(Base):
    __tablename__ = 'test_cases'

    id = Column(Integer, primary_key=True)
    bank_id = Column(String(50), ForeignKey('banks.bank_id', ondelete='CASCADE'), nullable=False)
    policy_type_id = Column(String(50), ForeignKey('policy_types.policy_type_id', ondelete='CASCADE'), nullable=False)

    # Test case metadata
    test_case_name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # 'boundary', 'positive', 'negative', 'edge_case', 'regression'
    priority = Column(Integer, default=1)  # 1=high, 2=medium, 3=low

    # Test data
    applicant_data = Column(JSONB, nullable=False)
    policy_data = Column(JSONB)

    # Expected results
    expected_decision = Column(String(50))  # 'approved', 'rejected', 'pending'
    expected_reasons = Column(ARRAY(Text))  # Array of expected reasons
    expected_risk_category = Column(Integer)  # Expected risk score 1-5

    # Metadata
    document_hash = Column(String(64))
    source_document = Column(String(500))

    # Auto-generated flag
    is_auto_generated = Column(Boolean, default=False)
    generation_method = Column(String(50))  # 'llm', 'manual', 'template', 'boundary_analysis'

    # Active/versioning
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))

    # Relationships
    bank = relationship("Bank")
    policy_type = relationship("PolicyType")
    executions = relationship("TestCaseExecution", back_populates="test_case", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_test_cases_bank_policy', 'bank_id', 'policy_type_id'),
        Index('idx_test_cases_category', 'category'),
        Index('idx_test_cases_priority', 'priority'),
        Index('idx_test_cases_active', 'is_active'),
        Index('idx_test_cases_document_hash', 'document_hash'),
    )


class TestCaseExecution(Base):
    __tablename__ = 'test_case_executions'

    id = Column(Integer, primary_key=True)
    test_case_id = Column(Integer, ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False)

    # Execution details
    execution_id = Column(String(100), nullable=False)  # UUID for tracking
    container_id = Column(String(200))  # Which Drools container was used

    # Actual results
    actual_decision = Column(String(50))
    actual_reasons = Column(ARRAY(Text))
    actual_risk_category = Column(Integer)

    # Full response
    request_payload = Column(JSONB)
    response_payload = Column(JSONB)

    # Test result
    test_passed = Column(Boolean)
    pass_reason = Column(Text)
    fail_reason = Column(Text)

    # Performance metrics
    execution_time_ms = Column(Integer)

    # Audit fields
    executed_at = Column(DateTime, default=datetime.utcnow)
    executed_by = Column(String(100))

    # Relationships
    test_case = relationship("TestCase", back_populates="executions")

    __table_args__ = (
        Index('idx_test_executions_test_case', 'test_case_id'),
        Index('idx_test_executions_execution_id', 'execution_id'),
        Index('idx_test_executions_passed', 'test_passed'),
        Index('idx_test_executions_executed_at', 'executed_at'),
    )


class DatabaseService:
    """Service class for database operations"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            database_url: PostgreSQL connection string. If None, uses DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'postgresql://underwriting_user:underwriting_pass@localhost:5432/underwriting_db'
        )

        self.engine = create_engine(self.database_url, pool_pre_ping=True, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        logger.info(f"Database service initialized with URL: {self.database_url.split('@')[1] if '@' in self.database_url else 'localhost'}")

    @contextmanager
    def get_session(self) -> Session:
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    # Bank operations
    def create_bank(self, bank_id: str, bank_name: str, description: str = None, contact_email: str = None) -> Bank:
        """Create or update a bank"""
        with self.get_session() as session:
            bank = session.query(Bank).filter_by(bank_id=bank_id).first()
            if bank:
                bank.bank_name = bank_name
                bank.description = description
                bank.contact_email = contact_email
                bank.updated_at = datetime.utcnow()
            else:
                bank = Bank(
                    bank_id=bank_id,
                    bank_name=bank_name,
                    description=description,
                    contact_email=contact_email
                )
                session.add(bank)
            session.commit()
            session.refresh(bank)
            return bank

    def get_bank(self, bank_id: str) -> Optional[Dict[str, Any]]:
        """Get a bank by ID as dictionary"""
        with self.get_session() as session:
            bank = session.query(Bank).filter_by(bank_id=bank_id).first()
            if not bank:
                return None

            # Convert to dictionary within session context
            return {
                'bank_id': bank.bank_id,
                'bank_name': bank.bank_name,
                'description': bank.description,
                'contact_email': bank.contact_email,
                'is_active': bank.is_active,
                'created_at': bank.created_at.isoformat() if bank.created_at else None,
                'updated_at': bank.updated_at.isoformat() if bank.updated_at else None
            }

    def list_banks(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all banks as dictionaries"""
        with self.get_session() as session:
            query = session.query(Bank)
            if active_only:
                query = query.filter_by(is_active=True)
            banks = query.all()

            # Convert to dictionaries within session context
            return [{
                'bank_id': bank.bank_id,
                'bank_name': bank.bank_name,
                'description': bank.description,
                'contact_email': bank.contact_email,
                'is_active': bank.is_active,
                'created_at': bank.created_at.isoformat() if bank.created_at else None,
                'updated_at': bank.updated_at.isoformat() if bank.updated_at else None
            } for bank in banks]

    # Policy Type operations
    def create_policy_type(self, policy_type_id: str, policy_name: str, description: str = None, category: str = None) -> PolicyType:
        """Create or update a policy type"""
        with self.get_session() as session:
            policy_type = session.query(PolicyType).filter_by(policy_type_id=policy_type_id).first()
            if policy_type:
                policy_type.policy_name = policy_name
                policy_type.description = description
                policy_type.category = category
                policy_type.updated_at = datetime.utcnow()
            else:
                policy_type = PolicyType(
                    policy_type_id=policy_type_id,
                    policy_name=policy_name,
                    description=description,
                    category=category
                )
                session.add(policy_type)
            session.commit()
            session.refresh(policy_type)
            return policy_type

    def get_policy_type(self, policy_type_id: str) -> Optional[Dict[str, Any]]:
        """Get a policy type by ID as dictionary"""
        with self.get_session() as session:
            pt = session.query(PolicyType).filter_by(policy_type_id=policy_type_id).first()
            if not pt:
                return None

            # Convert to dictionary within session context
            return {
                'policy_type_id': pt.policy_type_id,
                'policy_name': pt.policy_name,
                'description': pt.description,
                'category': pt.category,
                'is_active': pt.is_active,
                'created_at': pt.created_at.isoformat() if pt.created_at else None,
                'updated_at': pt.updated_at.isoformat() if pt.updated_at else None
            }

    def list_policy_types(self, active_only: bool = True, category: str = None) -> List[Dict[str, Any]]:
        """List all policy types as dictionaries"""
        with self.get_session() as session:
            query = session.query(PolicyType)
            if active_only:
                query = query.filter_by(is_active=True)
            if category:
                query = query.filter_by(category=category)
            policy_types = query.all()

            # Convert to dictionaries within session context
            return [{
                'policy_type_id': pt.policy_type_id,
                'policy_name': pt.policy_name,
                'description': pt.description,
                'category': pt.category,
                'is_active': pt.is_active,
                'created_at': pt.created_at.isoformat() if pt.created_at else None,
                'updated_at': pt.updated_at.isoformat() if pt.updated_at else None
            } for pt in policy_types]

    # Container operations
    def register_container(self, container_data: Dict[str, Any]) -> RuleContainer:
        """Register a new rule container or update if already exists"""
        with self.get_session() as session:
            # Ensure bank and policy type exist
            bank_id = container_data.get('bank_id')
            policy_type_id = container_data.get('policy_type_id')
            container_id = container_data.get('container_id')

            # Check if container with this container_id already exists
            existing_container = session.query(RuleContainer).filter_by(
                container_id=container_id
            ).first()

            if existing_container:
                # Update existing container
                for key, value in container_data.items():
                    if hasattr(existing_container, key) and key != 'id':
                        setattr(existing_container, key, value)
                existing_container.updated_at = datetime.utcnow()
                existing_container.is_active = True
                session.commit()
                session.refresh(existing_container)
                logger.info(f"Updated existing container {container_id} for {bank_id}/{policy_type_id}")
                return existing_container

            # Deactivate old containers for this bank+policy combination
            old_containers = session.query(RuleContainer).filter_by(
                bank_id=bank_id,
                policy_type_id=policy_type_id,
                is_active=True
            ).all()

            for old_container in old_containers:
                old_container.is_active = False
                old_container.status = 'stopped'
                old_container.stopped_at = datetime.utcnow()

            # Create new container
            container = RuleContainer(**container_data)
            session.add(container)
            session.commit()
            session.refresh(container)

            logger.info(f"Registered new container {container.container_id} for {bank_id}/{policy_type_id}")
            return container

    def _container_to_dict(self, container: RuleContainer) -> Dict[str, Any]:
        """Convert RuleContainer object to dictionary"""
        return {
            'id': container.id,
            'container_id': container.container_id,
            'bank_id': container.bank_id,
            'policy_type_id': container.policy_type_id,
            'platform': container.platform,
            'container_name': container.container_name,
            'endpoint': container.endpoint,
            'port': container.port,
            'status': container.status,
            'health_check_url': container.health_check_url,
            'last_health_check': container.last_health_check.isoformat() if container.last_health_check else None,
            'health_status': container.health_status,
            'failure_reason': container.failure_reason,
            'document_hash': container.document_hash,
            's3_policy_url': container.s3_policy_url,
            's3_jar_url': container.s3_jar_url,
            's3_drl_url': container.s3_drl_url,
            's3_excel_url': container.s3_excel_url,
            's3_test_harness_url': container.s3_test_harness_url,
            'version': container.version,
            'is_active': container.is_active,
            'cpu_limit': container.cpu_limit,
            'memory_limit': container.memory_limit,
            'deployed_at': container.deployed_at.isoformat() if container.deployed_at else None,
            'updated_at': container.updated_at.isoformat() if container.updated_at else None,
            'stopped_at': container.stopped_at.isoformat() if container.stopped_at else None
        }

    def get_container_by_id(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get a container by its container_id as dictionary"""
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(container_id=container_id).first()
            if not container:
                return None
            return self._container_to_dict(container)

    def get_container_by_db_id(self, db_id: int) -> Optional[Dict[str, Any]]:
        """Get a container by its database ID as dictionary"""
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(id=db_id).first()
            if not container:
                return None
            return self._container_to_dict(container)

    def get_active_container(self, bank_id: str, policy_type_id: str) -> Optional[Dict[str, Any]]:
        """Get the active container for a bank and policy type as dictionary"""
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(
                bank_id=bank_id,
                policy_type_id=policy_type_id,
                is_active=True
            ).first()
            if not container:
                return None
            return self._container_to_dict(container)

    def list_containers(self, bank_id: str = None, policy_type_id: str = None, status: str = None, active_only: bool = False) -> List[Dict[str, Any]]:
        """List containers with optional filters as dictionaries"""
        with self.get_session() as session:
            query = session.query(RuleContainer)

            if bank_id:
                query = query.filter_by(bank_id=bank_id)
            if policy_type_id:
                query = query.filter_by(policy_type_id=policy_type_id)
            if status:
                query = query.filter_by(status=status)
            if active_only:
                query = query.filter_by(is_active=True)

            containers = query.order_by(RuleContainer.deployed_at.desc()).all()

            # Convert to dictionaries within session context using helper
            return [self._container_to_dict(c) for c in containers]

    def update_container_status(self, container_id: str, status: str, health_status: str = None, failure_reason: str = None) -> Optional[RuleContainer]:
        """Update container status and health"""
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(container_id=container_id).first()
            if container:
                container.status = status
                if health_status:
                    container.health_status = health_status
                container.last_health_check = datetime.utcnow()
                if failure_reason:
                    container.failure_reason = failure_reason
                if status == 'stopped':
                    container.stopped_at = datetime.utcnow()
                    container.is_active = False
                session.commit()
                session.refresh(container)
                logger.info(f"Updated container {container_id} status to {status}")
            return container

    def update_container_urls(self, container_id: str, s3_jar_url: str = None, s3_drl_url: str = None, s3_excel_url: str = None, s3_policy_url: str = None, s3_test_harness_url: str = None) -> Optional[RuleContainer]:
        """Update container S3 artifact URLs"""
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(container_id=container_id).first()
            if container:
                if s3_jar_url:
                    container.s3_jar_url = s3_jar_url
                if s3_drl_url:
                    container.s3_drl_url = s3_drl_url
                if s3_excel_url:
                    container.s3_excel_url = s3_excel_url
                if s3_policy_url:
                    container.s3_policy_url = s3_policy_url
                if s3_test_harness_url:
                    container.s3_test_harness_url = s3_test_harness_url
                session.commit()
                session.refresh(container)
            return container

    def delete_container(self, container_id: str) -> bool:
        """Delete a container (soft delete by marking inactive)"""
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(container_id=container_id).first()
            if container:
                container.is_active = False
                container.status = 'stopped'
                container.stopped_at = datetime.utcnow()
                session.commit()
                logger.info(f"Deleted container {container_id}")
                return True
            return False

    def update_container_version(self, container_id: str, version: int) -> Optional[RuleContainer]:
        """Update container version number"""
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(container_id=container_id).first()
            if container:
                container.version = version
                container.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(container)
                logger.info(f"Updated container {container_id} version to {version}")
            return container

    def log_deployment_history(self, container_id: str, bank_id: str, policy_type_id: str,
                              action: str, version: int, changes_description: str = None,
                              deployed_by: str = None) -> Optional[ContainerDeploymentHistory]:
        """Log deployment history entry"""
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(container_id=container_id).first()
            if not container:
                logger.warning(f"Container {container_id} not found for history logging")
                return None
            
            history = ContainerDeploymentHistory(
                container_id=container.id,
                bank_id=bank_id,
                policy_type_id=policy_type_id,
                action=action,
                version=version,
                platform=container.platform,
                endpoint=container.endpoint,
                document_hash=container.document_hash,
                changes_description=changes_description,
                deployed_by=deployed_by or "system"
            )
            session.add(history)
            session.commit()
            session.refresh(history)
            logger.info(f"Logged {action} action for container {container_id}")
            return history

    # Request tracking
    def log_request(self, request_data: Dict[str, Any]) -> RuleRequest:
        """Log a rule request for analytics"""
        with self.get_session() as session:
            request = RuleRequest(**request_data)
            session.add(request)
            session.commit()
            session.refresh(request)
            return request

    def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get statistics for a container"""
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(container_id=container_id).first()
            if not container:
                return None

            requests = session.query(RuleRequest).filter_by(container_id=container.id).all()

            total_requests = len(requests)
            successful_requests = sum(1 for r in requests if r.status == 'success')
            failed_requests = sum(1 for r in requests if r.status == 'error')
            avg_time = sum(r.execution_time_ms for r in requests if r.execution_time_ms) / total_requests if total_requests > 0 else 0

            return {
                'container_id': container_id,
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'avg_execution_time_ms': avg_time,
                'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0
            }

    # Extracted Rules methods
    def save_extracted_rules(self, bank_id: str, policy_type_id: str, rules: List[Dict[str, Any]],
                            source_document: str = None, document_hash: str = None) -> List[int]:
        """
        Save extracted rules to database

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            rules: List of extracted rules with keys: rule_name, requirement, category
            source_document: Source document name
            document_hash: Hash of source document

        Returns:
            List of created rule IDs
        """
        try:
            with self.get_session() as session:
                # Deactivate existing rules for this bank/policy combination
                session.query(ExtractedRule).filter_by(
                    bank_id=bank_id,
                    policy_type_id=policy_type_id,
                    is_active=True
                ).update({'is_active': False})

                created_ids = []
                for rule_data in rules:
                    extracted_rule = ExtractedRule(
                        bank_id=bank_id,
                        policy_type_id=policy_type_id,
                        rule_name=rule_data.get('rule_name', rule_data.get('Rule', 'Unknown Rule')),
                        requirement=rule_data.get('requirement', rule_data.get('Requirement', '')),
                        category=rule_data.get('category', rule_data.get('Category', 'General')),
                        source_document=source_document or rule_data.get('source_document', rule_data.get('Source Document', '')),
                        page_number=rule_data.get('page_number'),
                        clause_reference=rule_data.get('clause_reference'),
                        document_hash=document_hash,
                        is_active=True
                    )
                    session.add(extracted_rule)
                    session.flush()
                    created_ids.append(extracted_rule.id)

                session.commit()
                logger.info(f"Saved {len(created_ids)} extracted rules for {bank_id}/{policy_type_id}")
                return created_ids

        except Exception as e:
            logger.error(f"Error saving extracted rules: {e}")
            return []

    def get_extracted_rules(self, bank_id: str, policy_type_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get extracted rules for a bank and policy type

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            active_only: Only return active rules

        Returns:
            List of rule dictionaries
        """
        try:
            with self.get_session() as session:
                query = session.query(ExtractedRule).filter_by(
                    bank_id=bank_id,
                    policy_type_id=policy_type_id
                )

                if active_only:
                    query = query.filter_by(is_active=True)

                rules = query.order_by(ExtractedRule.category, ExtractedRule.rule_name).all()

                return [{
                    'id': rule.id,
                    'rule_name': rule.rule_name,
                    'requirement': rule.requirement,
                    'category': rule.category,
                    'source_document': rule.source_document,
                    'page_number': rule.page_number,
                    'clause_reference': rule.clause_reference,
                    'document_hash': rule.document_hash,
                    'extraction_timestamp': rule.extraction_timestamp.isoformat() if rule.extraction_timestamp else None,
                    'is_active': rule.is_active,
                    'created_at': rule.created_at.isoformat() if rule.created_at else None,
                    'updated_at': rule.updated_at.isoformat() if rule.updated_at else None
                } for rule in rules]

        except Exception as e:
            logger.error(f"Error fetching extracted rules: {e}")
            return []

    def delete_extracted_rules(self, bank_id: str, policy_type_id: str) -> bool:
        """
        Delete all extracted rules for a bank and policy type

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.query(ExtractedRule).filter_by(
                    bank_id=bank_id,
                    policy_type_id=policy_type_id
                ).delete()
                session.commit()
                logger.info(f"Deleted extracted rules for {bank_id}/{policy_type_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting extracted rules: {e}")
            return False

    # Policy Extraction Queries methods
    def save_extraction_queries(self, bank_id: str, policy_type_id: str,
                                queries_data: List[Dict[str, Any]],
                                document_hash: str, source_document: str = None) -> List[int]:
        """
        Save extraction queries and Textract responses to database

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            queries_data: List of queries with keys: query_text, response_text, confidence_score
            document_hash: Hash of source document
            source_document: Source document path or S3 URL

        Returns:
            List of created query IDs
        """
        try:
            with self.get_session() as session:
                # Deactivate existing queries for this bank/policy/document combination
                session.query(PolicyExtractionQuery).filter_by(
                    bank_id=bank_id,
                    policy_type_id=policy_type_id,
                    document_hash=document_hash,
                    is_active=True
                ).update({'is_active': False})

                created_ids = []
                for idx, query_data in enumerate(queries_data, start=1):
                    extraction_query = PolicyExtractionQuery(
                        bank_id=bank_id,
                        policy_type_id=policy_type_id,
                        query_text=query_data.get('query_text', query_data.get('query', '')),
                        response_text=query_data.get('response_text', query_data.get('response', '')),
                        confidence_score=query_data.get('confidence_score', query_data.get('confidence')),
                        page_number=query_data.get('page_number'),
                        clause_reference=query_data.get('clause_reference'),
                        document_hash=document_hash,
                        source_document=source_document or query_data.get('source_document', ''),
                        extraction_method=query_data.get('extraction_method', 'textract'),
                        query_order=idx,
                        is_active=True
                    )
                    session.add(extraction_query)
                    session.flush()
                    created_ids.append(extraction_query.id)

                session.commit()
                logger.info(f"Saved {len(created_ids)} extraction queries for {bank_id}/{policy_type_id}")
                return created_ids

        except Exception as e:
            logger.error(f"Error saving extraction queries: {e}")
            return []

    def get_extraction_queries(self, bank_id: str, policy_type_id: str,
                               document_hash: str = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get extraction queries and responses for a bank and policy type

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            document_hash: Optional document hash filter
            active_only: Only return active queries

        Returns:
            List of query dictionaries
        """
        try:
            with self.get_session() as session:
                query = session.query(PolicyExtractionQuery).filter_by(
                    bank_id=bank_id,
                    policy_type_id=policy_type_id
                )

                if document_hash:
                    query = query.filter_by(document_hash=document_hash)

                if active_only:
                    query = query.filter_by(is_active=True)

                queries = query.order_by(PolicyExtractionQuery.query_order).all()

                return [{
                    'id': q.id,
                    'query_text': q.query_text,
                    'response_text': q.response_text,
                    'confidence_score': float(q.confidence_score) if q.confidence_score is not None else None,
                    'page_number': q.page_number,
                    'clause_reference': q.clause_reference,
                    'document_hash': q.document_hash,
                    'source_document': q.source_document,
                    'extraction_method': q.extraction_method,
                    'query_order': q.query_order,
                    'is_active': q.is_active,
                    'created_at': q.created_at.isoformat() if q.created_at else None,
                    'updated_at': q.updated_at.isoformat() if q.updated_at else None
                } for q in queries]

        except Exception as e:
            logger.error(f"Error fetching extraction queries: {e}")
            return []

    def delete_extraction_queries(self, bank_id: str, policy_type_id: str, document_hash: str = None) -> bool:
        """
        Delete extraction queries for a bank and policy type

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            document_hash: Optional document hash to delete specific document queries

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                query = session.query(PolicyExtractionQuery).filter_by(
                    bank_id=bank_id,
                    policy_type_id=policy_type_id
                )

                if document_hash:
                    query = query.filter_by(document_hash=document_hash)

                query.delete()
                session.commit()
                logger.info(f"Deleted extraction queries for {bank_id}/{policy_type_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting extraction queries: {e}")
            return False

    # Utility methods
    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    # Hierarchical Rules operations
    def save_hierarchical_rules(self, bank_id: str, policy_type_id: str, rules_tree: List[Dict[str, Any]],
                                document_hash: str = None, source_document: str = None) -> List[int]:
        """
        Save hierarchical rules tree to database

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            rules_tree: List of root-level rules, each with optional 'dependencies' array
            document_hash: Hash of source document
            source_document: Path/name of source document

        Returns:
            List of created rule IDs
        """
        with self.get_session() as session:
            # Deactivate existing hierarchical rules for this bank/policy combination
            session.query(HierarchicalRule).filter_by(
                bank_id=bank_id,
                policy_type_id=policy_type_id,
                is_active=True
            ).update({'is_active': False})

            # Flush the deactivation before inserting new records
            session.flush()

            created_ids = []

            def save_rule_recursive(rule_data: Dict[str, Any], parent_id: int = None, level: int = 0, order: int = 0) -> int:
                """Recursively save a rule and its children"""
                rule = HierarchicalRule(
                    bank_id=bank_id,
                    policy_type_id=policy_type_id,
                    rule_id=rule_data.get('id', ''),
                    name=rule_data.get('name', ''),
                    description=rule_data.get('description'),
                    expected=rule_data.get('expected'),
                    actual=rule_data.get('actual'),
                    confidence=rule_data.get('confidence'),
                    passed=rule_data.get('passed'),
                    parent_id=parent_id,
                    level=level,
                    order_index=order,
                    page_number=rule_data.get('page_number'),
                    clause_reference=rule_data.get('clause_reference'),
                    document_hash=document_hash,
                    source_document=source_document
                )
                session.add(rule)
                session.flush()  # Get the ID without committing

                created_ids.append(rule.id)

                # Process dependencies (children)
                if 'dependencies' in rule_data and rule_data['dependencies']:
                    for idx, child_rule in enumerate(rule_data['dependencies']):
                        save_rule_recursive(child_rule, parent_id=rule.id, level=level + 1, order=idx)

                return rule.id

            # Save all root-level rules
            for idx, root_rule in enumerate(rules_tree):
                save_rule_recursive(root_rule, parent_id=None, level=0, order=idx)

            session.commit()
            logger.info(f"Saved {len(created_ids)} hierarchical rules for {bank_id}/{policy_type_id}")
            return created_ids

    def get_hierarchical_rules(self, bank_id: str, policy_type_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get hierarchical rules tree for a bank and policy type

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            active_only: Only return active rules

        Returns:
            List of root-level rules with nested dependencies
        """
        with self.get_session() as session:
            query = session.query(HierarchicalRule).filter_by(
                bank_id=bank_id,
                policy_type_id=policy_type_id
            )
            if active_only:
                query = query.filter_by(is_active=True)

            all_rules = query.order_by(HierarchicalRule.level, HierarchicalRule.order_index).all()

            if not all_rules:
                return []

            # Build a lookup dictionary
            rules_by_id = {}
            for rule in all_rules:
                rules_by_id[rule.id] = {
                    'id': rule.rule_id,
                    'name': rule.name,
                    'description': rule.description,
                    'expected': rule.expected,
                    'actual': rule.actual,
                    'confidence': rule.confidence,
                    'passed': rule.passed,
                    'page_number': rule.page_number,
                    'clause_reference': rule.clause_reference,
                    'dependencies': []
                }

            # Build tree structure
            root_rules = []
            for rule in all_rules:
                rule_dict = rules_by_id[rule.id]

                if rule.parent_id is None:
                    # Root level rule
                    root_rules.append(rule_dict)
                else:
                    # Child rule - add to parent's dependencies
                    if rule.parent_id in rules_by_id:
                        rules_by_id[rule.parent_id]['dependencies'].append(rule_dict)

            return root_rules

    def update_hierarchical_rules(self, bank_id: str, policy_type_id: str, 
                                  updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update hierarchical rules fields (expected, actual, confidence, passed, etc.)
        
        Supports updating by either:
        - rule_id: Dot notation identifier (e.g., "1.1", "1.2.3")
        - id: Database ID
        
        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            updates: List of update objects, each containing:
                - rule_id OR id: Rule identifier
                - expected: (optional) Expected value/condition
                - actual: (optional) Actual value/result
                - confidence: (optional) Confidence score (0.0-1.0)
                - passed: (optional) Pass/fail status (boolean)
                - description: (optional) Rule description
                - name: (optional) Rule name
        
        Returns:
            Dictionary with:
                - updated_count: Number of rules updated
                - updated_ids: List of database IDs that were updated
                - errors: List of errors if any rules failed to update
        
        Example:
            updates = [
                {
                    "rule_id": "1.1",
                    "expected": "Age >= 18",
                    "actual": "Age = 25",
                    "confidence": 0.95,
                    "passed": True
                },
                {
                    "id": 42,  # or use database ID directly
                    "expected": "Credit Score >= 600",
                    "confidence": 0.88
                }
            ]
        """
        with self.get_session() as session:
            updated_ids = []
            errors = []
            
            for update_data in updates:
                try:
                    # Find the rule by either rule_id or database id
                    rule = None
                    
                    if 'id' in update_data:
                        # Update by database ID
                        rule = session.query(HierarchicalRule).filter_by(
                            id=update_data['id'],
                            bank_id=bank_id,
                            policy_type_id=policy_type_id
                        ).first()
                        identifier = f"id={update_data['id']}"
                    elif 'rule_id' in update_data:
                        # Update by dot notation rule_id
                        rule = session.query(HierarchicalRule).filter_by(
                            rule_id=update_data['rule_id'],
                            bank_id=bank_id,
                            policy_type_id=policy_type_id
                        ).first()
                        identifier = f"rule_id={update_data['rule_id']}"
                    else:
                        errors.append({
                            "error": "Missing identifier",
                            "message": "Each update must have either 'id' or 'rule_id'"
                        })
                        continue
                    
                    if not rule:
                        errors.append({
                            "error": "Rule not found",
                            "identifier": identifier,
                            "bank_id": bank_id,
                            "policy_type_id": policy_type_id
                        })
                        continue
                    
                    # Update fields if provided
                    updated = False
                    if 'expected' in update_data:
                        rule.expected = update_data['expected']
                        updated = True
                    if 'actual' in update_data:
                        rule.actual = update_data['actual']
                        updated = True
                    if 'confidence' in update_data:
                        rule.confidence = float(update_data['confidence'])
                        updated = True
                    if 'passed' in update_data:
                        rule.passed = bool(update_data['passed'])
                        updated = True
                    if 'description' in update_data:
                        rule.description = update_data['description']
                        updated = True
                    if 'name' in update_data:
                        rule.name = update_data['name']
                        updated = True
                    if 'page_number' in update_data:
                        rule.page_number = update_data['page_number']
                        updated = True
                    if 'clause_reference' in update_data:
                        rule.clause_reference = update_data['clause_reference']
                        updated = True
                    
                    if updated:
                        # updated_at will be automatically updated by SQLAlchemy
                        session.flush()
                        updated_ids.append(rule.id)
                        logger.info(f"Updated hierarchical rule {identifier} for {bank_id}/{policy_type_id}")
                    
                except Exception as e:
                    errors.append({
                        "error": str(e),
                        "update_data": update_data
                    })
            
            # Commit all updates
            if updated_ids:
                session.commit()
            
            result = {
                "updated_count": len(updated_ids),
                "updated_ids": updated_ids,
                "errors": errors
            }
            
            logger.info(f"Updated {len(updated_ids)} hierarchical rules for {bank_id}/{policy_type_id}")
            return result

    def delete_hierarchical_rules(self, bank_id: str, policy_type_id: str) -> int:
        """
        Delete all hierarchical rules for a bank and policy type

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier

        Returns:
            Number of rules deleted
        """
        with self.get_session() as session:
            deleted_count = session.query(HierarchicalRule).filter_by(
                bank_id=bank_id,
                policy_type_id=policy_type_id
            ).delete()
            session.commit()
            logger.info(f"Deleted {deleted_count} hierarchical rules for {bank_id}/{policy_type_id}")
            return deleted_count

    def get_banks_with_policies(self) -> List[Dict[str, Any]]:
        """Get all banks with their available policy types"""
        with self.get_session() as session:
            banks = session.query(Bank).filter_by(is_active=True).all()
            result = []

            for bank in banks:
                containers = session.query(RuleContainer).filter_by(
                    bank_id=bank.bank_id,
                    is_active=True
                ).all()

                policies = list(set([c.policy_type_id for c in containers]))

                result.append({
                    'bank_id': bank.bank_id,
                    'bank_name': bank.bank_name,
                    'available_policies': policies,
                    'total_containers': len(containers)
                })

            return result

    # ==================== TEST CASES METHODS ====================

    def save_test_cases(self, bank_id: str, policy_type_id: str, test_cases: List[Dict[str, Any]],
                       document_hash: str = None, source_document: str = None) -> List[int]:
        """
        Save multiple test cases to the database

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            test_cases: List of test case dictionaries
            document_hash: Optional document hash
            source_document: Optional source document path/URL

        Returns:
            List of created test case IDs
        """
        with self.get_session() as session:
            # Deactivate existing test cases for this bank/policy combination
            session.query(TestCase).filter_by(
                bank_id=bank_id,
                policy_type_id=policy_type_id,
                is_active=True
            ).update({'is_active': False})

            # Flush the deactivation before inserting new records
            session.flush()

            test_case_ids = []

            for tc in test_cases:
                test_case = TestCase(
                    bank_id=bank_id,
                    policy_type_id=policy_type_id,
                    test_case_name=tc.get('test_case_name'),
                    description=tc.get('description'),
                    category=tc.get('category', 'positive'),
                    priority=tc.get('priority', 1),
                    applicant_data=tc.get('applicant_data'),
                    policy_data=tc.get('policy_data'),
                    expected_decision=tc.get('expected_decision'),
                    expected_reasons=tc.get('expected_reasons', []),
                    expected_risk_category=tc.get('expected_risk_category'),
                    document_hash=document_hash,
                    source_document=source_document,
                    is_auto_generated=tc.get('is_auto_generated', False),
                    generation_method=tc.get('generation_method', 'manual'),
                    created_by=tc.get('created_by', 'system')
                )

                session.add(test_case)
                session.flush()  # Get the ID
                test_case_ids.append(test_case.id)

            session.commit()
            logger.info(f"Saved {len(test_case_ids)} test cases for {bank_id}/{policy_type_id}")
            return test_case_ids

    def get_test_cases(self, bank_id: str, policy_type_id: str,
                       category: str = None, is_active: bool = True) -> List[Dict[str, Any]]:
        """
        Get test cases for a bank and policy type

        Args:
            bank_id: Bank identifier
            policy_type_id: Policy type identifier
            category: Optional filter by category
            is_active: Filter by active status (default True)

        Returns:
            List of test case dictionaries
        """
        with self.get_session() as session:
            query = session.query(TestCase).filter_by(
                bank_id=bank_id,
                policy_type_id=policy_type_id,
                is_active=is_active
            )

            if category:
                query = query.filter_by(category=category)

            test_cases = query.order_by(TestCase.priority, TestCase.created_at).all()

            return [{
                'id': tc.id,
                'test_case_name': tc.test_case_name,
                'description': tc.description,
                'category': tc.category,
                'priority': tc.priority,
                'applicant_data': tc.applicant_data,
                'policy_data': tc.policy_data,
                'expected_decision': tc.expected_decision,
                'expected_reasons': tc.expected_reasons,
                'expected_risk_category': tc.expected_risk_category,
                'is_auto_generated': tc.is_auto_generated,
                'generation_method': tc.generation_method,
                'created_at': tc.created_at.isoformat() if tc.created_at else None
            } for tc in test_cases]

    def get_test_case_by_id(self, test_case_id: int) -> Optional[Dict[str, Any]]:
        """Get a single test case by ID"""
        with self.get_session() as session:
            tc = session.query(TestCase).filter_by(id=test_case_id).first()

            if not tc:
                return None

            return {
                'id': tc.id,
                'bank_id': tc.bank_id,
                'policy_type_id': tc.policy_type_id,
                'test_case_name': tc.test_case_name,
                'description': tc.description,
                'category': tc.category,
                'priority': tc.priority,
                'applicant_data': tc.applicant_data,
                'policy_data': tc.policy_data,
                'expected_decision': tc.expected_decision,
                'expected_reasons': tc.expected_reasons,
                'expected_risk_category': tc.expected_risk_category,
                'is_auto_generated': tc.is_auto_generated,
                'generation_method': tc.generation_method,
                'document_hash': tc.document_hash,
                'source_document': tc.source_document,
                'created_at': tc.created_at.isoformat() if tc.created_at else None,
                'updated_at': tc.updated_at.isoformat() if tc.updated_at else None
            }

    def save_test_execution(self, test_case_id: int, execution_data: Dict[str, Any]) -> int:
        """
        Save test case execution results

        Args:
            test_case_id: Test case ID
            execution_data: Dictionary containing execution details

        Returns:
            Execution ID
        """
        with self.get_session() as session:
            execution = TestCaseExecution(
                test_case_id=test_case_id,
                execution_id=execution_data.get('execution_id'),
                container_id=execution_data.get('container_id'),
                actual_decision=execution_data.get('actual_decision'),
                actual_reasons=execution_data.get('actual_reasons', []),
                actual_risk_category=execution_data.get('actual_risk_category'),
                request_payload=execution_data.get('request_payload'),
                response_payload=execution_data.get('response_payload'),
                test_passed=execution_data.get('test_passed'),
                pass_reason=execution_data.get('pass_reason'),
                fail_reason=execution_data.get('fail_reason'),
                execution_time_ms=execution_data.get('execution_time_ms'),
                executed_by=execution_data.get('executed_by', 'system')
            )

            session.add(execution)
            session.commit()
            logger.info(f"Saved test execution {execution.execution_id} for test case {test_case_id}")
            return execution.id

    def get_test_executions(self, test_case_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get test execution history for a test case

        Args:
            test_case_id: Test case ID
            limit: Maximum number of executions to return (default 10)

        Returns:
            List of execution dictionaries
        """
        with self.get_session() as session:
            executions = session.query(TestCaseExecution).filter_by(
                test_case_id=test_case_id
            ).order_by(TestCaseExecution.executed_at.desc()).limit(limit).all()

            return [{
                'id': ex.id,
                'execution_id': ex.execution_id,
                'container_id': ex.container_id,
                'actual_decision': ex.actual_decision,
                'actual_reasons': ex.actual_reasons,
                'actual_risk_category': ex.actual_risk_category,
                'test_passed': ex.test_passed,
                'pass_reason': ex.pass_reason,
                'fail_reason': ex.fail_reason,
                'execution_time_ms': ex.execution_time_ms,
                'executed_at': ex.executed_at.isoformat() if ex.executed_at else None,
                'executed_by': ex.executed_by
            } for ex in executions]

    def get_test_case_summary(self, bank_id: str = None, policy_type_id: str = None) -> List[Dict[str, Any]]:
        """
        Get test case summary statistics using the database view

        Args:
            bank_id: Optional bank filter
            policy_type_id: Optional policy type filter

        Returns:
            List of test case summaries with execution statistics
        """
        with self.get_session() as session:
            # Query the view directly
            query = "SELECT * FROM test_case_summary WHERE 1=1"
            params = {}

            if bank_id:
                query += " AND bank_id = :bank_id"
                params['bank_id'] = bank_id

            if policy_type_id:
                query += " AND policy_type_id = :policy_type_id"
                params['policy_type_id'] = policy_type_id

            query += " ORDER BY priority, test_case_name"

            result = session.execute(text(query), params)
            rows = result.fetchall()

            return [{
                'id': row[0],
                'bank_id': row[1],
                'policy_type_id': row[2],
                'test_case_name': row[3],
                'category': row[4],
                'priority': row[5],
                'is_auto_generated': row[6],
                'created_at': row[7].isoformat() if row[7] else None,
                'total_executions': row[8],
                'passed_executions': row[9],
                'failed_executions': row[10],
                'pass_rate': float(row[11]) if row[11] else 0.0,
                'last_execution_at': row[12].isoformat() if row[12] else None
            } for row in rows]

    #  ==================== TEST EXECUTION METHODS ====================

    def save_test_execution(self, execution_data: Dict[str, Any]) -> int:
        """
        Save a test execution result to the database

        Args:
            execution_data: Dictionary with execution details

        Returns:
            ID of created execution record
        """
        with self.get_session() as session:
            execution = TestCaseExecution(
                test_case_id=execution_data['test_case_id'],
                execution_id=execution_data['execution_id'],
                container_id=execution_data.get('container_id'),
                actual_decision=execution_data.get('actual_decision'),
                actual_reasons=execution_data.get('actual_reasons', []),
                actual_risk_category=execution_data.get('actual_risk_category'),
                request_payload=execution_data.get('request_payload'),
                response_payload=execution_data.get('response_payload'),
                test_passed=execution_data.get('test_passed'),
                pass_reason=execution_data.get('pass_reason'),
                fail_reason=execution_data.get('fail_reason'),
                execution_time_ms=execution_data.get('execution_time_ms'),
                executed_at=execution_data.get('executed_at', datetime.utcnow()),
                executed_by=execution_data.get('executed_by', 'system')
            )

            session.add(execution)
            session.flush()
            execution_id = execution.id
            session.commit()

            logger.info(f"Saved test execution {execution_id} for test case {execution_data['test_case_id']}")
            return execution_id

    def get_test_executions(self, test_case_id: int = None,
                           container_id: str = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get test execution history

        Args:
            test_case_id: Optional filter by test case
            container_id: Optional filter by container
            limit: Maximum number of records to return

        Returns:
            List of execution dictionaries
        """
        with self.get_session() as session:
            query = session.query(TestCaseExecution)

            if test_case_id:
                query = query.filter_by(test_case_id=test_case_id)

            if container_id:
                query = query.filter_by(container_id=container_id)

            executions = query.order_by(TestCaseExecution.executed_at.desc()).limit(limit).all()

            return [{
                'id': e.id,
                'test_case_id': e.test_case_id,
                'execution_id': e.execution_id,
                'container_id': e.container_id,
                'actual_decision': e.actual_decision,
                'actual_reasons': e.actual_reasons,
                'actual_risk_category': e.actual_risk_category,
                'test_passed': e.test_passed,
                'pass_reason': e.pass_reason,
                'fail_reason': e.fail_reason,
                'execution_time_ms': e.execution_time_ms,
                'executed_at': e.executed_at.isoformat() if e.executed_at else None,
                'executed_by': e.executed_by
            } for e in executions]

    def get_test_cases_raw(self, bank_id: str, policy_type: str, is_active: bool = True):
        """
        Get test case model objects (not dictionaries) for test execution

        Args:
            bank_id: Bank identifier
            policy_type: Policy type identifier
            is_active: Filter by active status

        Returns:
            List of TestCase model objects
        """
        with self.get_session() as session:
            test_cases = session.query(TestCase).filter_by(
                bank_id=bank_id,
                policy_type_id=policy_type,
                is_active=is_active
            ).order_by(TestCase.priority, TestCase.created_at).all()

            # Detach from session to avoid lazy loading issues
            session.expunge_all()
            return test_cases

    def get_test_cases_by_ids(self, test_case_ids: list) -> List[Dict[str, Any]]:
        """
        Get test cases by specific IDs (for current workflow run)

        Args:
            test_case_ids: List of test case IDs to retrieve

        Returns:
            List of test case dictionaries
        """
        if not test_case_ids:
            return []

        with self.get_session() as session:
            test_cases = session.query(TestCase).filter(
                TestCase.id.in_(test_case_ids)
            ).order_by(TestCase.priority, TestCase.created_at).all()

            # Convert to dictionaries (same format as get_test_cases)
            return [{
                'id': tc.id,
                'test_case_name': tc.test_case_name,
                'description': tc.description,
                'category': tc.category,
                'priority': tc.priority,
                'applicant_data': tc.applicant_data,
                'policy_data': tc.policy_data,
                'expected_decision': tc.expected_decision,
                'expected_reasons': tc.expected_reasons,
                'expected_risk_category': tc.expected_risk_category,
                'is_auto_generated': tc.is_auto_generated,
                'generation_method': tc.generation_method,
                'created_at': tc.created_at.isoformat() if tc.created_at else None
            } for tc in test_cases]

    def get_container(self, container_id: str):
        """
        Get container by ID

        Args:
            container_id: Container identifier

        Returns:
            RuleContainer model object or None
        """
        with self.get_session() as session:
            container = session.query(RuleContainer).filter_by(
                container_id=container_id
            ).first()

            if container:
                session.expunge(container)
            return container

    def delete_test_case(self, test_case_id: int) -> bool:
        """
        Soft delete a test case (sets is_active to False)

        Args:
            test_case_id: Test case ID

        Returns:
            True if deleted, False if not found
        """
        with self.get_session() as session:
            test_case = session.query(TestCase).filter_by(id=test_case_id).first()

            if not test_case:
                return False

            test_case.is_active = False
            test_case.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Soft deleted test case {test_case_id}")
            return True


# Singleton instance
_db_service_instance = None

def get_database_service() -> DatabaseService:
    """Get or create database service singleton"""
    global _db_service_instance
    if _db_service_instance is None:
        _db_service_instance = DatabaseService()
    return _db_service_instance
