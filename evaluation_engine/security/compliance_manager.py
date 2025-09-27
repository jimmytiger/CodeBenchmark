"""
GDPR and SOC2 Compliance Manager

Provides comprehensive compliance measures with data privacy controls.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import hashlib
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)

class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    GDPR = "GDPR"
    SOC2 = "SOC2"
    HIPAA = "HIPAA"
    PCI_DSS = "PCI_DSS"
    ISO27001 = "ISO27001"

class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    PII = "PII"  # Personally Identifiable Information

class ConsentStatus(Enum):
    """Data processing consent status"""
    GIVEN = "GIVEN"
    WITHDRAWN = "WITHDRAWN"
    PENDING = "PENDING"
    NOT_REQUIRED = "NOT_REQUIRED"

class ProcessingPurpose(Enum):
    """Data processing purposes"""
    EVALUATION = "EVALUATION"
    ANALYTICS = "ANALYTICS"
    SECURITY = "SECURITY"
    COMPLIANCE = "COMPLIANCE"
    RESEARCH = "RESEARCH"

@dataclass
class DataSubject:
    """Represents a data subject (individual whose data is processed)"""
    subject_id: str
    email: Optional[str] = None
    created_at: datetime = None
    consent_status: ConsentStatus = ConsentStatus.NOT_REQUIRED
    consent_date: Optional[datetime] = None
    consent_purposes: List[ProcessingPurpose] = None
    data_retention_period: Optional[int] = None  # days
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.consent_purposes is None:
            self.consent_purposes = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class DataProcessingRecord:
    """Records data processing activities for compliance"""
    record_id: str
    data_subject_id: str
    processing_purpose: ProcessingPurpose
    data_categories: List[str]
    processing_date: datetime
    retention_period: int  # days
    legal_basis: str
    processor: str
    data_location: str
    security_measures: List[str]
    third_party_transfers: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.third_party_transfers is None:
            self.third_party_transfers = []
        if self.metadata is None:
            self.metadata = {}
        if not self.record_id:
            self.record_id = str(uuid.uuid4())

@dataclass
class ComplianceViolation:
    """Represents a compliance violation"""
    violation_id: str
    framework: ComplianceFramework
    violation_type: str
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    detected_at: datetime
    affected_data_subjects: List[str]
    remediation_actions: List[str]
    status: str  # OPEN, INVESTIGATING, REMEDIATED, CLOSED
    due_date: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.violation_id:
            self.violation_id = f"CV-{hashlib.sha256(f'{self.framework.value}{self.violation_type}{self.detected_at}'.encode()).hexdigest()[:8].upper()}"

class GDPRCompliance:
    """GDPR compliance implementation"""
    
    def __init__(self):
        self.data_subjects: Dict[str, DataSubject] = {}
        self.processing_records: List[DataProcessingRecord] = []
        self.consent_records: Dict[str, Dict[str, Any]] = {}
        self.data_retention_policies: Dict[str, int] = {
            'evaluation_data': 30,  # 30 days
            'audit_logs': 2555,     # 7 years
            'security_events': 365, # 1 year
            'user_data': 90         # 90 days
        }
    
    def register_data_subject(self, subject_id: str, email: Optional[str] = None,
                            consent_purposes: Optional[List[ProcessingPurpose]] = None) -> DataSubject:
        """Register a new data subject"""
        subject = DataSubject(
            subject_id=subject_id,
            email=email,
            consent_purposes=consent_purposes or []
        )
        
        self.data_subjects[subject_id] = subject
        logger.info(f"Registered data subject: {subject_id}")
        return subject
    
    def record_consent(self, subject_id: str, purposes: List[ProcessingPurpose],
                      consent_method: str = "explicit") -> bool:
        """Record data processing consent"""
        if subject_id not in self.data_subjects:
            self.register_data_subject(subject_id)
        
        subject = self.data_subjects[subject_id]
        subject.consent_status = ConsentStatus.GIVEN
        subject.consent_date = datetime.utcnow()
        subject.consent_purposes = purposes
        
        # Record consent details
        self.consent_records[subject_id] = {
            'consent_date': subject.consent_date.isoformat(),
            'purposes': [p.value for p in purposes],
            'method': consent_method,
            'ip_address': None,  # Would be captured in real implementation
            'user_agent': None   # Would be captured in real implementation
        }
        
        logger.info(f"Recorded consent for subject {subject_id}: {[p.value for p in purposes]}")
        return True
    
    def withdraw_consent(self, subject_id: str, purposes: Optional[List[ProcessingPurpose]] = None) -> bool:
        """Withdraw data processing consent"""
        if subject_id not in self.data_subjects:
            return False
        
        subject = self.data_subjects[subject_id]
        
        if purposes is None:
            # Withdraw all consent
            subject.consent_status = ConsentStatus.WITHDRAWN
            subject.consent_purposes = []
        else:
            # Withdraw specific purposes
            for purpose in purposes:
                if purpose in subject.consent_purposes:
                    subject.consent_purposes.remove(purpose)
            
            if not subject.consent_purposes:
                subject.consent_status = ConsentStatus.WITHDRAWN
        
        logger.info(f"Withdrew consent for subject {subject_id}")
        return True
    
    def record_processing_activity(self, subject_id: str, purpose: ProcessingPurpose,
                                 data_categories: List[str], processor: str,
                                 legal_basis: str = "consent") -> DataProcessingRecord:
        """Record data processing activity"""
        record = DataProcessingRecord(
            record_id="",
            data_subject_id=subject_id,
            processing_purpose=purpose,
            data_categories=data_categories,
            processing_date=datetime.utcnow(),
            retention_period=self.data_retention_policies.get('evaluation_data', 30),
            legal_basis=legal_basis,
            processor=processor,
            data_location="EU",  # Configurable
            security_measures=["encryption", "access_control", "audit_logging"]
        )
        
        self.processing_records.append(record)
        logger.info(f"Recorded processing activity: {record.record_id}")
        return record
    
    def handle_data_subject_request(self, subject_id: str, request_type: str) -> Dict[str, Any]:
        """Handle data subject rights requests (Article 15-22)"""
        if subject_id not in self.data_subjects:
            return {'status': 'error', 'message': 'Data subject not found'}
        
        subject = self.data_subjects[subject_id]
        
        if request_type == "access":
            # Right of access (Article 15)
            return self._handle_access_request(subject_id)
        elif request_type == "rectification":
            # Right to rectification (Article 16)
            return self._handle_rectification_request(subject_id)
        elif request_type == "erasure":
            # Right to erasure (Article 17)
            return self._handle_erasure_request(subject_id)
        elif request_type == "portability":
            # Right to data portability (Article 20)
            return self._handle_portability_request(subject_id)
        else:
            return {'status': 'error', 'message': f'Unknown request type: {request_type}'}
    
    def _handle_access_request(self, subject_id: str) -> Dict[str, Any]:
        """Handle data access request"""
        subject = self.data_subjects[subject_id]
        subject_records = [r for r in self.processing_records if r.data_subject_id == subject_id]
        
        return {
            'status': 'success',
            'data': {
                'subject_info': asdict(subject),
                'processing_records': [asdict(r) for r in subject_records],
                'consent_records': self.consent_records.get(subject_id, {}),
                'generated_at': datetime.utcnow().isoformat()
            }
        }
    
    def _handle_rectification_request(self, subject_id: str) -> Dict[str, Any]:
        """Handle data rectification request"""
        # In a real implementation, this would allow updating incorrect data
        return {
            'status': 'success',
            'message': 'Rectification request processed',
            'actions_required': ['manual_review', 'data_update']
        }
    
    def _handle_erasure_request(self, subject_id: str) -> Dict[str, Any]:
        """Handle data erasure request (right to be forgotten)"""
        if subject_id not in self.data_subjects:
            return {'status': 'error', 'message': 'Data subject not found'}
        
        # Remove data subject
        del self.data_subjects[subject_id]
        
        # Remove processing records
        self.processing_records = [r for r in self.processing_records if r.data_subject_id != subject_id]
        
        # Remove consent records
        if subject_id in self.consent_records:
            del self.consent_records[subject_id]
        
        logger.info(f"Processed erasure request for subject {subject_id}")
        
        return {
            'status': 'success',
            'message': 'Data erasure completed',
            'erased_at': datetime.utcnow().isoformat()
        }
    
    def _handle_portability_request(self, subject_id: str) -> Dict[str, Any]:
        """Handle data portability request"""
        access_data = self._handle_access_request(subject_id)
        
        if access_data['status'] == 'success':
            # Format data for portability (structured, machine-readable)
            portable_data = {
                'format': 'JSON',
                'version': '1.0',
                'exported_at': datetime.utcnow().isoformat(),
                'data': access_data['data']
            }
            
            return {
                'status': 'success',
                'portable_data': portable_data
            }
        
        return access_data
    
    def check_retention_compliance(self) -> List[Dict[str, Any]]:
        """Check data retention compliance"""
        violations = []
        current_time = datetime.utcnow()
        
        for record in self.processing_records:
            retention_deadline = record.processing_date + timedelta(days=record.retention_period)
            
            if current_time > retention_deadline:
                violations.append({
                    'record_id': record.record_id,
                    'subject_id': record.data_subject_id,
                    'processing_date': record.processing_date.isoformat(),
                    'retention_deadline': retention_deadline.isoformat(),
                    'days_overdue': (current_time - retention_deadline).days,
                    'violation_type': 'retention_period_exceeded'
                })
        
        return violations

class SOC2Compliance:
    """SOC2 compliance implementation"""
    
    def __init__(self):
        self.trust_service_criteria = {
            'security': ['CC6.1', 'CC6.2', 'CC6.3', 'CC6.4', 'CC6.5', 'CC6.6', 'CC6.7', 'CC6.8'],
            'availability': ['A1.1', 'A1.2', 'A1.3'],
            'processing_integrity': ['PI1.1', 'PI1.2', 'PI1.3'],
            'confidentiality': ['C1.1', 'C1.2'],
            'privacy': ['P1.1', 'P2.1', 'P3.1', 'P4.1', 'P5.1', 'P6.1', 'P7.1', 'P8.1']
        }
        self.control_assessments: Dict[str, Dict[str, Any]] = {}
        self.evidence_collection: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def assess_control(self, control_id: str, assessment_result: str,
                      evidence: List[str], assessor: str) -> bool:
        """Assess SOC2 control implementation"""
        self.control_assessments[control_id] = {
            'control_id': control_id,
            'assessment_result': assessment_result,  # EFFECTIVE, INEFFECTIVE, NOT_TESTED
            'evidence': evidence,
            'assessor': assessor,
            'assessment_date': datetime.utcnow().isoformat(),
            'next_assessment_due': (datetime.utcnow() + timedelta(days=90)).isoformat()
        }
        
        logger.info(f"Assessed SOC2 control {control_id}: {assessment_result}")
        return True
    
    def collect_evidence(self, control_id: str, evidence_type: str,
                        evidence_data: Dict[str, Any]) -> str:
        """Collect evidence for SOC2 controls"""
        evidence_id = str(uuid.uuid4())
        
        evidence_record = {
            'evidence_id': evidence_id,
            'control_id': control_id,
            'evidence_type': evidence_type,
            'evidence_data': evidence_data,
            'collected_at': datetime.utcnow().isoformat(),
            'collector': 'system'
        }
        
        self.evidence_collection[control_id].append(evidence_record)
        logger.info(f"Collected evidence {evidence_id} for control {control_id}")
        return evidence_id
    
    def generate_control_report(self, control_category: str) -> Dict[str, Any]:
        """Generate SOC2 control assessment report"""
        if control_category not in self.trust_service_criteria:
            raise ValueError(f"Unknown control category: {control_category}")
        
        controls = self.trust_service_criteria[control_category]
        report = {
            'category': control_category,
            'controls': [],
            'summary': {
                'total_controls': len(controls),
                'effective': 0,
                'ineffective': 0,
                'not_tested': 0
            },
            'generated_at': datetime.utcnow().isoformat()
        }
        
        for control_id in controls:
            assessment = self.control_assessments.get(control_id, {})
            evidence = self.evidence_collection.get(control_id, [])
            
            control_report = {
                'control_id': control_id,
                'assessment': assessment,
                'evidence_count': len(evidence),
                'status': assessment.get('assessment_result', 'NOT_TESTED')
            }
            
            report['controls'].append(control_report)
            
            # Update summary
            status = control_report['status']
            if status == 'EFFECTIVE':
                report['summary']['effective'] += 1
            elif status == 'INEFFECTIVE':
                report['summary']['ineffective'] += 1
            else:
                report['summary']['not_tested'] += 1
        
        return report

class ComplianceManager:
    """Comprehensive compliance and monitoring system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled_frameworks = self.config.get('frameworks', [ComplianceFramework.GDPR, ComplianceFramework.SOC2])
        
        # Initialize compliance modules
        self.gdpr = GDPRCompliance()
        self.soc2 = SOC2Compliance()
        
        # Compliance violations tracking
        self.violations: Dict[str, ComplianceViolation] = {}
        
        # Monitoring and reporting
        self.compliance_reports: List[Dict[str, Any]] = []
        self.audit_trail: List[Dict[str, Any]] = []
        
        # Data classification
        self.data_classifications: Dict[str, DataClassification] = {}
        
        # Automated monitoring
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self):
        """Start automated compliance monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started compliance monitoring")
    
    async def stop_monitoring(self):
        """Stop automated compliance monitoring"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped compliance monitoring")
    
    async def _monitoring_loop(self):
        """Main compliance monitoring loop"""
        while self.is_monitoring:
            try:
                # Check GDPR compliance
                if ComplianceFramework.GDPR in self.enabled_frameworks:
                    await self._check_gdpr_compliance()
                
                # Check SOC2 compliance
                if ComplianceFramework.SOC2 in self.enabled_frameworks:
                    await self._check_soc2_compliance()
                
                # Generate compliance reports
                await self._generate_compliance_reports()
                
                # Clean up old data
                await self._cleanup_expired_data()
                
                # Sleep before next check
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in compliance monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _check_gdpr_compliance(self):
        """Check GDPR compliance violations"""
        # Check data retention compliance
        retention_violations = self.gdpr.check_retention_compliance()
        
        for violation_data in retention_violations:
            violation = ComplianceViolation(
                violation_id="",
                framework=ComplianceFramework.GDPR,
                violation_type="data_retention_exceeded",
                description=f"Data retention period exceeded for record {violation_data['record_id']}",
                severity="HIGH",
                detected_at=datetime.utcnow(),
                affected_data_subjects=[violation_data['subject_id']],
                remediation_actions=["delete_expired_data", "update_retention_policy"],
                status="OPEN",
                due_date=datetime.utcnow() + timedelta(days=30),
                metadata=violation_data
            )
            
            self.violations[violation.violation_id] = violation
            logger.warning(f"GDPR violation detected: {violation.violation_id}")
    
    async def _check_soc2_compliance(self):
        """Check SOC2 compliance violations"""
        # Check if controls are assessed regularly
        current_time = datetime.utcnow()
        
        for category, controls in self.soc2.trust_service_criteria.items():
            for control_id in controls:
                assessment = self.soc2.control_assessments.get(control_id)
                
                if not assessment:
                    # Control not assessed
                    violation = ComplianceViolation(
                        violation_id="",
                        framework=ComplianceFramework.SOC2,
                        violation_type="control_not_assessed",
                        description=f"SOC2 control {control_id} has not been assessed",
                        severity="MEDIUM",
                        detected_at=current_time,
                        affected_data_subjects=[],
                        remediation_actions=["assess_control", "collect_evidence"],
                        status="OPEN",
                        due_date=current_time + timedelta(days=30),
                        metadata={'control_id': control_id, 'category': category}
                    )
                    
                    self.violations[violation.violation_id] = violation
                
                elif assessment.get('assessment_result') == 'INEFFECTIVE':
                    # Control is ineffective
                    violation = ComplianceViolation(
                        violation_id="",
                        framework=ComplianceFramework.SOC2,
                        violation_type="ineffective_control",
                        description=f"SOC2 control {control_id} is assessed as ineffective",
                        severity="HIGH",
                        detected_at=current_time,
                        affected_data_subjects=[],
                        remediation_actions=["remediate_control", "reassess_control"],
                        status="OPEN",
                        due_date=current_time + timedelta(days=14),
                        metadata={'control_id': control_id, 'assessment': assessment}
                    )
                    
                    self.violations[violation.violation_id] = violation
    
    async def _generate_compliance_reports(self):
        """Generate periodic compliance reports"""
        report = {
            'report_id': str(uuid.uuid4()),
            'generated_at': datetime.utcnow().isoformat(),
            'frameworks': [f.value for f in self.enabled_frameworks],
            'violations': {
                'total': len(self.violations),
                'by_framework': {},
                'by_severity': {},
                'open': len([v for v in self.violations.values() if v.status == 'OPEN'])
            },
            'gdpr_summary': {},
            'soc2_summary': {}
        }
        
        # Count violations by framework and severity
        for violation in self.violations.values():
            framework = violation.framework.value
            severity = violation.severity
            
            if framework not in report['violations']['by_framework']:
                report['violations']['by_framework'][framework] = 0
            report['violations']['by_framework'][framework] += 1
            
            if severity not in report['violations']['by_severity']:
                report['violations']['by_severity'][severity] = 0
            report['violations']['by_severity'][severity] += 1
        
        # GDPR summary
        if ComplianceFramework.GDPR in self.enabled_frameworks:
            report['gdpr_summary'] = {
                'data_subjects': len(self.gdpr.data_subjects),
                'processing_records': len(self.gdpr.processing_records),
                'consent_records': len(self.gdpr.consent_records)
            }
        
        # SOC2 summary
        if ComplianceFramework.SOC2 in self.enabled_frameworks:
            total_controls = sum(len(controls) for controls in self.soc2.trust_service_criteria.values())
            assessed_controls = len(self.soc2.control_assessments)
            
            report['soc2_summary'] = {
                'total_controls': total_controls,
                'assessed_controls': assessed_controls,
                'assessment_coverage': (assessed_controls / total_controls * 100) if total_controls > 0 else 0
            }
        
        self.compliance_reports.append(report)
        
        # Keep only last 100 reports
        if len(self.compliance_reports) > 100:
            self.compliance_reports = self.compliance_reports[-100:]
    
    async def _cleanup_expired_data(self):
        """Clean up expired data according to retention policies"""
        current_time = datetime.utcnow()
        
        # Clean up GDPR processing records
        expired_records = []
        for record in self.gdpr.processing_records:
            retention_deadline = record.processing_date + timedelta(days=record.retention_period)
            if current_time > retention_deadline:
                expired_records.append(record)
        
        for record in expired_records:
            self.gdpr.processing_records.remove(record)
            logger.info(f"Cleaned up expired processing record: {record.record_id}")
        
        # Clean up old compliance reports (keep for 2 years)
        cutoff_date = current_time - timedelta(days=730)
        self.compliance_reports = [
            report for report in self.compliance_reports
            if datetime.fromisoformat(report['generated_at']) > cutoff_date
        ]
    
    def classify_data(self, data_id: str, classification: DataClassification,
                     justification: str) -> bool:
        """Classify data according to sensitivity levels"""
        self.data_classifications[data_id] = classification
        
        # Record classification in audit trail
        self.audit_trail.append({
            'action': 'data_classification',
            'data_id': data_id,
            'classification': classification.value,
            'justification': justification,
            'timestamp': datetime.utcnow().isoformat(),
            'user': 'system'
        })
        
        logger.info(f"Classified data {data_id} as {classification.value}")
        return True
    
    def handle_data_breach(self, breach_description: str, affected_data_subjects: List[str],
                          breach_type: str, discovered_at: Optional[datetime] = None) -> str:
        """Handle data breach notification and response"""
        if discovered_at is None:
            discovered_at = datetime.utcnow()
        
        breach_id = f"BREACH-{hashlib.sha256(f'{breach_description}{discovered_at}'.encode()).hexdigest()[:8].upper()}"
        
        # Create compliance violation for the breach
        violation = ComplianceViolation(
            violation_id="",
            framework=ComplianceFramework.GDPR,  # Assuming GDPR for data breaches
            violation_type="data_breach",
            description=f"Data breach: {breach_description}",
            severity="CRITICAL",
            detected_at=discovered_at,
            affected_data_subjects=affected_data_subjects,
            remediation_actions=[
                "contain_breach",
                "assess_impact",
                "notify_authorities",
                "notify_data_subjects"
            ],
            status="OPEN",
            due_date=discovered_at + timedelta(hours=72),  # GDPR 72-hour notification requirement
            metadata={
                'breach_id': breach_id,
                'breach_type': breach_type,
                'affected_count': len(affected_data_subjects)
            }
        )
        
        self.violations[violation.violation_id] = violation
        
        # Record in audit trail
        self.audit_trail.append({
            'action': 'data_breach_reported',
            'breach_id': breach_id,
            'violation_id': violation.violation_id,
            'affected_subjects': len(affected_data_subjects),
            'timestamp': discovered_at.isoformat(),
            'user': 'system'
        })
        
        logger.critical(f"Data breach reported: {breach_id}")
        return breach_id
    
    def remediate_violation(self, violation_id: str, remediation_notes: str,
                           remediated_by: str) -> bool:
        """Mark compliance violation as remediated"""
        if violation_id not in self.violations:
            return False
        
        violation = self.violations[violation_id]
        violation.status = "REMEDIATED"
        violation.resolved_at = datetime.utcnow()
        violation.metadata['remediation_notes'] = remediation_notes
        violation.metadata['remediated_by'] = remediated_by
        
        # Record in audit trail
        self.audit_trail.append({
            'action': 'violation_remediated',
            'violation_id': violation_id,
            'remediated_by': remediated_by,
            'timestamp': datetime.utcnow().isoformat(),
            'notes': remediation_notes
        })
        
        logger.info(f"Remediated compliance violation: {violation_id}")
        return True
    
    def generate_compliance_report(self, framework: ComplianceFramework,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        # Filter violations by framework and date range
        relevant_violations = [
            v for v in self.violations.values()
            if v.framework == framework and start_date <= v.detected_at <= end_date
        ]
        
        report = {
            'framework': framework.value,
            'report_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'generated_at': datetime.utcnow().isoformat(),
            'violations': {
                'total': len(relevant_violations),
                'open': len([v for v in relevant_violations if v.status == 'OPEN']),
                'remediated': len([v for v in relevant_violations if v.status == 'REMEDIATED']),
                'by_type': {},
                'by_severity': {}
            },
            'compliance_status': 'COMPLIANT',
            'recommendations': []
        }
        
        # Count violations by type and severity
        for violation in relevant_violations:
            vtype = violation.violation_type
            severity = violation.severity
            
            if vtype not in report['violations']['by_type']:
                report['violations']['by_type'][vtype] = 0
            report['violations']['by_type'][vtype] += 1
            
            if severity not in report['violations']['by_severity']:
                report['violations']['by_severity'][severity] = 0
            report['violations']['by_severity'][severity] += 1
        
        # Determine overall compliance status
        open_critical = len([v for v in relevant_violations 
                           if v.status == 'OPEN' and v.severity == 'CRITICAL'])
        open_high = len([v for v in relevant_violations 
                       if v.status == 'OPEN' and v.severity == 'HIGH'])
        
        if open_critical > 0:
            report['compliance_status'] = 'NON_COMPLIANT'
            report['recommendations'].append('Address critical compliance violations immediately')
        elif open_high > 0:
            report['compliance_status'] = 'AT_RISK'
            report['recommendations'].append('Address high-severity compliance violations')
        
        # Framework-specific details
        if framework == ComplianceFramework.GDPR:
            report['gdpr_details'] = {
                'data_subjects': len(self.gdpr.data_subjects),
                'processing_records': len(self.gdpr.processing_records),
                'consent_records': len(self.gdpr.consent_records),
                'data_subject_requests': 0  # Would track actual requests
            }
        elif framework == ComplianceFramework.SOC2:
            report['soc2_details'] = self.soc2.generate_control_report('security')
        
        return report
    
    def export_audit_trail(self, output_file: str, start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None):
        """Export audit trail for compliance reporting"""
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=90)
        
        # Filter audit trail by date range
        filtered_trail = [
            entry for entry in self.audit_trail
            if start_date <= datetime.fromisoformat(entry['timestamp']) <= end_date
        ]
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                'audit_trail': filtered_trail,
                'export_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'exported_at': datetime.utcnow().isoformat(),
                'total_entries': len(filtered_trail)
            }, f, indent=2, default=str)
        
        logger.info(f"Exported audit trail to {output_path}: {len(filtered_trail)} entries")
    
    def get_compliance_status(self) -> Dict[str, Any]:
        """Get overall compliance system status"""
        return {
            'status': 'active' if self.is_monitoring else 'stopped',
            'enabled_frameworks': [f.value for f in self.enabled_frameworks],
            'total_violations': len(self.violations),
            'open_violations': len([v for v in self.violations.values() if v.status == 'OPEN']),
            'data_subjects': len(self.gdpr.data_subjects),
            'processing_records': len(self.gdpr.processing_records),
            'soc2_controls_assessed': len(self.soc2.control_assessments),
            'audit_trail_entries': len(self.audit_trail),
            'compliance_reports': len(self.compliance_reports)
        }