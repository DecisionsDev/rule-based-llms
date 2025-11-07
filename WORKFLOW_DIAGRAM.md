# Underwriting Rule Generation Workflow

This document provides visual diagrams of the complete underwriting workflow system.

## Complete Workflow Diagram

```mermaid
flowchart TD
    Start([User Request]) --> API[POST /process_policy_from_s3]

    API --> Input{Input Parameters}
    Input -->|Required| S3URL[S3 URL to Policy PDF]
    Input -->|Optional| PolicyType[Policy Type: insurance/loan/auto]
    Input -->|Recommended| BankID[Bank ID: chase/bofa/wells-fargo]
    Input -->|Optional| ContainerID[Container ID Override]

    S3URL --> Step0[Step 0: Parse S3 URL]
    PolicyType --> Step0
    BankID --> Step0

    Step0 --> ContainerGen{Container ID<br/>Provided?}
    ContainerGen -->|No| AutoGen[Auto-generate:<br/>bank_id-policy_type-underwriting-rules]
    ContainerGen -->|Yes| UseProvided[Use Provided Container ID]

    AutoGen --> Step1
    UseProvided --> Step1

    Step1[Step 1: Extract Text from PDF] --> S3Read{S3 or Local?}
    S3Read -->|S3| ReadS3[Read PDF from S3 into Memory<br/>No Local Download]
    S3Read -->|Local| ReadLocal[Read from Local File]

    ReadS3 --> PyPDF2[PyPDF2: Extract Text]
    ReadLocal --> PyPDF2

    PyPDF2 --> Step2[Step 2: Generate Extraction Queries]

    Step2 --> QueryType{Template or<br/>LLM Generated?}
    QueryType -->|Template| TemplateQ[Use Template Queries<br/>for Policy Type]
    QueryType -->|LLM| LLMGen[LLM Generates Custom Queries<br/>Based on Document]

    TemplateQ --> Step3
    LLMGen --> Step3

    Step3[Step 3: Extract Structured Data] --> TextractCheck{AWS Textract<br/>Available?}

    TextractCheck -->|Yes| TextractS3{S3 Document?}
    TextractS3 -->|Yes| TextractNative[Textract with S3Object<br/>No Download Required]
    TextractS3 -->|No| TextractLocal[Textract with Local File]

    TextractCheck -->|No| MockExtract[Mock Extraction<br/>LLM-based Text Analysis]

    TextractNative --> Step4
    TextractLocal --> Step4
    MockExtract --> Step4

    Step4[Step 4: Generate Drools DRL Rules] --> RuleGen[LLM Generates:<br/>- DRL Rules<br/>- Decision Tables<br/>- Explanations]

    RuleGen --> Step5[Step 5: Automated Drools Deployment]

    Step5 --> TempDir[Create Temporary Directory]
    TempDir --> SaveDRL[Save DRL File]
    SaveDRL --> CreateKJar[Create KJar Structure<br/>Maven Project Layout]
    CreateKJar --> MavenBuild[Maven Build:<br/>mvn clean install]

    MavenBuild --> BuildSuccess{Build<br/>Success?}
    BuildSuccess -->|No| BuildFail[Status: Partial<br/>Manual Build Required]
    BuildSuccess -->|Yes| CopyFiles[Copy JAR & DRL to<br/>Temp Location for S3]

    CopyFiles --> DeployKIE[Deploy to Drools KIE Server]

    DeployKIE --> ContainerExists{Container<br/>Exists?}
    ContainerExists -->|Yes| Dispose[Dispose Old Container]
    Dispose --> CreateNew[Create New Container<br/>with New Version]
    ContainerExists -->|No| CreateNew

    CreateNew --> DeploySuccess{Deployment<br/>Success?}
    DeploySuccess -->|No| DeployFail[Status: Partial<br/>KJar Built, Deployment Failed]
    DeploySuccess -->|Yes| CleanTemp[Auto-Delete Temp Build Directory]

    CleanTemp --> Step6[Step 6: Upload Files to S3]

    Step6 --> UploadJAR[Upload JAR File<br/>s3://bucket/generated-rules/<br/>container_id/version/file.jar]
    UploadJAR --> UploadDRL[Upload DRL File<br/>s3://bucket/generated-rules/<br/>container_id/version/file.drl]

    UploadDRL --> CheckBank{Bank ID<br/>Provided?}
    CheckBank -->|Yes| GenerateExcel[Generate Excel Spreadsheet]
    CheckBank -->|No| SkipExcel[Skip Excel Generation]

    GenerateExcel --> ParseDRL[Parse DRL Rules:<br/>- Rule Names<br/>- Conditions<br/>- Actions<br/>- Priority]

    ParseDRL --> CreateExcel[Create Multi-Sheet Excel:<br/>1. Summary Sheet<br/>2. Rules Sheet<br/>3. Raw DRL Sheet]

    CreateExcel --> UploadExcel[Upload Excel to S3<br/>Filename: bank_id_policy_type_rules_timestamp.xlsx]

    UploadExcel --> CleanExcel[Delete Temp Excel File]
    SkipExcel --> FinalClean
    CleanExcel --> FinalClean[Clean Up All Temp Files]

    FinalClean --> Response[Return Response JSON]
    BuildFail --> Response
    DeployFail --> Response

    Response --> ResponseContent{Response Contains}
    ResponseContent --> RC1[container_id]
    ResponseContent --> RC2[status: completed/partial/failed]
    ResponseContent --> RC3[jar_s3_url]
    ResponseContent --> RC4[drl_s3_url]
    ResponseContent --> RC5[excel_s3_url]
    ResponseContent --> RC6[Detailed Steps Results]

    RC1 --> End([Workflow Complete])
    RC2 --> End
    RC3 --> End
    RC4 --> End
    RC5 --> End
    RC6 --> End

    style Start fill:#e1f5e1
    style End fill:#e1f5e1
    style Step1 fill:#e3f2fd
    style Step2 fill:#e3f2fd
    style Step3 fill:#e3f2fd
    style Step4 fill:#e3f2fd
    style Step5 fill:#e3f2fd
    style Step6 fill:#e3f2fd
    style GenerateExcel fill:#fff3e0
    style CreateExcel fill:#fff3e0
    style UploadExcel fill:#fff3e0
    style DeployKIE fill:#f3e5f5
    style CreateNew fill:#f3e5f5
```

## Multi-Tenant Container Architecture

```mermaid
graph TB
    subgraph "Bank: Chase"
        C1[chase-insurance-underwriting-rules]
        C2[chase-loan-underwriting-rules]
        C3[chase-auto-underwriting-rules]
    end

    subgraph "Bank: Bank of America"
        B1[bofa-insurance-underwriting-rules]
        B2[bofa-loan-underwriting-rules]
        B3[bofa-auto-underwriting-rules]
    end

    subgraph "Bank: Wells Fargo"
        W1[wellsfargo-insurance-underwriting-rules]
        W2[wellsfargo-loan-underwriting-rules]
        W3[wellsfargo-auto-underwriting-rules]
    end

    subgraph "Drools KIE Server"
        KIE[KIE Server<br/>Multiple Isolated Containers]
    end

    C1 --> KIE
    C2 --> KIE
    C3 --> KIE
    B1 --> KIE
    B2 --> KIE
    B3 --> KIE
    W1 --> KIE
    W2 --> KIE
    W3 --> KIE

    style C1 fill:#4fc3f7
    style C2 fill:#4fc3f7
    style C3 fill:#4fc3f7
    style B1 fill:#81c784
    style B2 fill:#81c784
    style B3 fill:#81c784
    style W1 fill:#ffb74d
    style W2 fill:#ffb74d
    style W3 fill:#ffb74d
    style KIE fill:#f06292
```

## S3 Storage Organization

```mermaid
graph TD
    S3[S3 Bucket: uw-data-extraction]

    S3 --> Policies[/policies/]
    S3 --> Rules[/generated-rules/]

    Policies --> P1[chase/insurance_2025.pdf]
    Policies --> P2[bofa/loan_policy.pdf]
    Policies --> P3[wellsfargo/auto_policy.pdf]

    Rules --> Container1[/chase-insurance-underwriting-rules/]
    Rules --> Container2[/bofa-loan-underwriting-rules/]
    Rules --> Container3[/wellsfargo-auto-underwriting-rules/]

    Container1 --> V1[/20250104.143000/]
    V1 --> V1JAR[chase-insurance...jar]
    V1 --> V1DRL[chase-insurance...drl]
    V1 --> V1XLSX[chase_insurance_rules_20250104_143000.xlsx]

    Container2 --> V2[/20250104.150000/]
    V2 --> V2JAR[bofa-loan...jar]
    V2 --> V2DRL[bofa-loan...drl]
    V2 --> V2XLSX[bofa_loan_rules_20250104_150000.xlsx]

    Container3 --> V3[/20250104.153000/]
    V3 --> V3JAR[wellsfargo-auto...jar]
    V3 --> V3DRL[wellsfargo-auto...drl]
    V3 --> V3XLSX[wellsfargo_auto_rules_20250104_153000.xlsx]

    style S3 fill:#ff6f00
    style Policies fill:#ffa726
    style Rules fill:#ffa726
    style V1XLSX fill:#66bb6a
    style V2XLSX fill:#66bb6a
    style V3XLSX fill:#66bb6a
```

## Excel Spreadsheet Structure

```mermaid
graph LR
    Excel[Excel Workbook:<br/>bank_id_policy_type_rules_timestamp.xlsx]

    Excel --> Sheet1[Summary Sheet]
    Excel --> Sheet2[Rules Sheet]
    Excel --> Sheet3[Raw DRL Sheet]

    Sheet1 --> S1C1[Bank ID: chase]
    Sheet1 --> S1C2[Policy Type: insurance]
    Sheet1 --> S1C3[Container ID: chase-insurance...]
    Sheet1 --> S1C4[Version: 20250104.143000]
    Sheet1 --> S1C5[Generated Date: 2025-01-04 14:30:00]
    Sheet1 --> S1C6[Total Rules: 12]

    Sheet2 --> S2C1[Rule Name]
    Sheet2 --> S2C2[Priority Salience]
    Sheet2 --> S2C3[Conditions When]
    Sheet2 --> S2C4[Actions Then]
    Sheet2 --> S2C5[Attributes]

    Sheet3 --> S3C1[Complete DRL Content<br/>for Technical Reference]

    style Excel fill:#4caf50
    style Sheet1 fill:#81c784
    style Sheet2 fill:#aed581
    style Sheet3 fill:#c5e1a5
```

## Update/Replacement Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Workflow
    participant Drools
    participant S3

    User->>API: POST /process_policy_from_s3<br/>bank_id=chase, policy_type=insurance
    API->>Workflow: Generate container_id:<br/>chase-insurance-underwriting-rules

    Note over Workflow: Process Steps 1-4<br/>Extract, Analyze, Generate Rules

    Workflow->>Drools: Check if container exists:<br/>chase-insurance-underwriting-rules

    alt Container Exists
        Drools-->>Workflow: Container found (version: v1)
        Workflow->>Drools: Dispose old container (v1)
        Drools-->>Workflow: Disposed successfully
    end

    Workflow->>Drools: Create new container (version: v2)
    Drools-->>Workflow: Container created with v2

    Workflow->>S3: Upload JAR (v2)
    Workflow->>S3: Upload DRL (v2)
    Workflow->>S3: Upload Excel (v2)

    S3-->>Workflow: All files uploaded

    Note over S3: Both v1 and v2 files<br/>preserved in S3<br/>for audit history

    Note over Drools: Only v2 active<br/>in KIE Server

    Workflow->>API: Return result with S3 URLs
    API->>User: Response:<br/>- container_id<br/>- jar_s3_url<br/>- drl_s3_url<br/>- excel_s3_url
```

## System Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Web UI / Swagger / Postman]
        CURL[cURL / Scripts]
    end

    subgraph "API Layer"
        Flask[Flask REST API<br/>Port 9000]
        Swagger[Swagger UI<br/>/rule-agent/docs]
    end

    subgraph "Workflow Orchestration"
        UW[UnderwritingWorkflow]
        PA[PolicyAnalyzerAgent]
        RG[RuleGeneratorAgent]
        EE[ExcelRulesExporter]
    end

    subgraph "External Services"
        Textract[AWS Textract<br/>Document Analysis]
        S3Svc[AWS S3<br/>Storage Service]
        LLM[LLM Service<br/>Watsonx/OpenAI/Ollama]
    end

    subgraph "Drools Components"
        DD[DroolsDeploymentService]
        Maven[Maven Build]
        KIE[Drools KIE Server<br/>Port 9060]
    end

    subgraph "Storage"
        S3[(S3 Bucket:<br/>uw-data-extraction)]
        TempFS[Temporary File System<br/>Auto-Cleanup]
    end

    UI --> Flask
    CURL --> Flask
    Flask --> Swagger
    Flask --> UW

    UW --> PA
    UW --> RG
    UW --> EE
    UW --> DD

    PA --> LLM
    RG --> LLM

    UW --> Textract
    UW --> S3Svc

    DD --> Maven
    Maven --> KIE

    S3Svc --> S3
    Textract --> S3
    DD --> TempFS
    EE --> TempFS

    S3 --> |JAR/DRL/Excel| S3Svc

    style Flask fill:#4fc3f7
    style UW fill:#81c784
    style LLM fill:#ffb74d
    style KIE fill:#f06292
    style S3 fill:#ff6f00
    style EE fill:#66bb6a
```

## Key Features

### 1. Zero Persistent Local Storage
- All files use temporary directories with automatic cleanup
- Input PDFs read directly from S3 into memory
- Maven builds in temp directories (auto-deleted after completion)
- Generated files (JAR, DRL, Excel) uploaded to S3 and then deleted locally

### 2. Multi-Tenant Isolation
- Separate containers per bank and policy type
- Format: `{bank_id}-{policy_type}-underwriting-rules`
- Examples:
  - `chase-insurance-underwriting-rules`
  - `bofa-loan-underwriting-rules`
  - `wellsfargo-auto-underwriting-rules`

### 3. Excel Export
- Automatically generated for each deployment (when bank_id provided)
- Filename includes bank and policy type: `{bank_id}_{policy_type}_rules_{timestamp}.xlsx`
- Three sheets: Summary, Parsed Rules, Raw DRL
- Uploaded to S3 alongside JAR and DRL files

### 4. Container Update Strategy
- Detects existing containers
- Disposes old version before creating new
- Preserves version history in S3
- Only latest version active in KIE Server

### 5. Flexible LLM Support
- Watsonx.ai
- OpenAI
- Ollama (local)
- Template queries (no LLM required)

### 6. AWS Integration
- Native S3 integration for document storage
- AWS Textract for intelligent data extraction
- Fallback to PyPDF2 + LLM when Textract unavailable
