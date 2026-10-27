"""Dicionário de skills: 726 termos de busca -> 406 skills canônicas.

Montado a partir do que realmente aparece nos currículos da amostra, não de
uma lista genérica de tecnologias. As frequências medidas estão no
README_FILTRO_SKILLS.md.

Sinônimos colapsam no canônico: ``amazon web services`` e ``aws`` viram AWS,
``core java``/``java 8`` viram Java, ``restful``/``rest api`` viram REST.
Assim o banco tem uma linha por skill, não uma por grafia.

Para adicionar: ``add("Nome Canônico", CATEGORIA, ["variante", ...])``.
Regras: no máximo 3 palavras por termo (o varredor usa n-gramas de até 3),
minúsculo, sem pontuação exceto ``+`` e ``#`` (que são preservados para C++
e C#). Plural é resolvido em tempo de busca, não precisa cadastrar.

Dois cuidados que vieram de falso positivo real:

- termo de uma letra (``R``, ``C``) casa com qualquer letra solta no texto.
  Por isso ``R`` não está aqui e C++/C# dependem de ``+``/``#`` preservados.
- ``Apache`` sozinho casava dentro de "Apache Kafka"/"Apache Storm". Agora
  ``Apache HTTP Server`` só casa com ``apache http``/``httpd``, e cada
  projeto Apache tem a sua própria variante.
"""

from __future__ import annotations

CATEGORIAS = (
    "LINGUAGEM", "FRAMEWORK", "BANCO", "BIGDATA", "CLOUD", "SERVIDOR",
    "FERRAMENTA", "METODOLOGIA", "ARTEFATO_BA", "GESTAO", "DOMINIO",
    "REGULATORIO", "SOFTSKILL",
)

CANON: dict[str, tuple[str, list[str]]] = {}

def add(canon, cat, variantes):
    CANON[canon] = (cat, sorted(set([canon.lower()] + variantes), key=lambda s: -len(s)))

L="LINGUAGEM"; F="FRAMEWORK"; B="BANCO"; BD="BIGDATA"; C="CLOUD"; S="SERVIDOR"
T="FERRAMENTA"; M="METODOLOGIA"; A="ARTEFATO_BA"; D="DOMINIO"; G="GESTAO"; R="REGULATORIO"; SS="SOFTSKILL"

# ---------------- LINGUAGEM
add("Java", L, ["core java","java 8","java8","java 7","java se"])
add("J2EE", L, ["jee","java ee","j2ee"])
add("Python", L, []); add("Scala", L, []); add("C#", L, ["c sharp","csharp"]); add("C++", L, ["cpp"])
add("JavaScript", L, ["java script"]); add("TypeScript", L, [])
add("SQL", L, []); add("PL/SQL", L, ["pl sql","plsql"]); add("T-SQL", L, ["t sql","tsql"])
add("PHP", L, []); add("Perl", L, []); add("Ruby", L, []); add("Golang", L, ["go lang"])
add("Shell Script", L, ["shell scripting","shell script","unix shell","bash script","korn shell"])
add("HTML", L, ["html5","html 5","xhtml","dhtml"]); add("CSS", L, ["css3","css 3","sass","scss","less"])
add("XML", L, []); add("XSLT", L, ["xsl","xslt"]); add("XPath", L, []); add("JSON", L, [])
add("VBScript", L, ["vb script","vbscript","visual basic"]); add(".NET", L, ["asp net","dot net","vb net"])
add("COBOL", L, []); add("ABAP", L, []); add("SAS", L, []); add("MATLAB", L, [])
add("Groovy", L, []); add("Kotlin", L, []); add("Swift", L, [])

# ---------------- FRAMEWORK / API
add("Spring", F, ["spring framework"]); add("Spring Boot", F, ["springboot"])
add("Spring MVC", F, []); add("Spring AOP", F, []); add("Spring IOC", F, ["spring ioc","spring di"])
add("Spring Batch", F, []); add("Spring Security", F, []); add("Spring Data", F, [])
add("Spring Cloud", F, []); add("Hibernate", F, []); add("Struts", F, ["struts 2","struts2"])
add("JSF", F, []); add("EJB", F, []); add("JPA", F, ["java persistence api"]); add("JDBC", F, [])
add("JMS", F, ["java messaging service"]); add("JNDI", F, [])
add("JTA", F, []); add("RMI", F, []); add("Servlets", F, ["servlet"]); add("JSP", F, ["jstl","tag libraries"])
add("SOAP", F, []); add("REST", F, ["restful","rest api","rest apis"])
add("JAX-WS", F, ["jax ws"]); add("JAX-RS", F, ["jax rs"]); add("JAX-RPC", F, ["jax rpc"])
add("JAXB", F, []); add("SAAJ", F, []); add("WSDL", F, []); add("UDDI", F, [])
add("Web Services", F, ["web service"]); add("Microservices", F, ["micro services","micro service"])
add("SOA", F, ["service oriented architecture"])
add("Angular", F, ["angularjs","angular js","angular 2","angular2","angular 4","angular 6"])
add("React", F, ["react js","reactjs"]); add("Node.js", F, ["node js","nodejs"])
add("jQuery", F, ["jquery ui"]); add("Bootstrap", F, []); add("AJAX", F, []); add("ExtJS", F, ["ext js"])
add("Swing", F, ["jfc"]); add("Apache Camel", F, ["camel"]); add("MuleSoft", F, ["mule esb","mule"])
add("Log4j", F, []); add("JUnit", F, []); add("Mockito", F, []); add("Drools", F, ["drools"]); add("Session Beans", F, ["session bean", "entity bean", "entity beans"]); add("TestNG", F, [])
add("Selenium", F, ["selenium webdriver","selenium rc"]); add("Cucumber", F, [])
add("Django", F, []); add("Flask", F, []); add("SAX", F, []); add("DOM", F, []); add("DTD", F, []); add("XSD", F, [])

# ---------------- BANCO
add("Oracle", B, ["oracle 10g","oracle 11g","oracle 12c","oracle 9i","oracle db"])
add("MySQL", B, ["my sql"]); add("SQL Server", B, ["ms sql server","microsoft sql server"])
add("PostgreSQL", B, ["postgres"]); add("DB2", B, []); add("Teradata", B, [])
add("MongoDB", B, ["mongo db"]); add("Cassandra", B, []); add("NoSQL", B, [])
add("Sybase", B, []); add("MS Access", B, ["microsoft access"]); add("DynamoDB", B, ["dynamo db"])
add("Redis", B, []); add("Neo4j", B, []); add("TOAD", B, []); add("SQL Developer", B, [])

# ---------------- BIG DATA / DADOS
add("Hadoop", BD, ["hdfs","apache hadoop"]); add("MapReduce", BD, ["map reduce"]); add("Spark", BD, ["apache spark"])
add("Spark SQL", BD, []); add("Spark Streaming", BD, []); add("Spark MLlib", BD, ["mllib","spark mlib"])
add("Kafka", BD, ["apache kafka"]); add("Sqoop", BD, []); add("Flume", BD, []); add("Oozie", BD, [])
add("Zookeeper", BD, []); add("Storm", BD, ["apache storm"]); add("Pig", BD, ["apache pig"]); add("Hive", BD, ["apache hive"])
add("HBase", BD, []); add("Impala", BD, []); add("YARN", BD, []); add("Cloudera", BD, [])
add("Hortonworks", BD, []); add("Elasticsearch", BD, ["elastic search"]); add("Kibana", BD, [])
add("Informatica", BD, []); add("DataStage", BD, ["data stage"]); add("SSIS", BD, []); add("SSRS", BD, [])
add("Talend", BD, []); add("Avro", BD, []); add("Parquet", BD, []); add("ORC", BD, []); add("RCFile", BD, [])
add("Data Warehouse", BD, ["data warehousing","datawarehouse","dwh"]); add("Data Lake", BD, [])
add("ETL", BD, []); add("OLAP", BD, []); add("OLTP", BD, [])
add("Dimensional Modeling", BD, ["star schema","snowflake schema","data mart"])
add("Data Mapping", A, ["data mappings"]); add("Data Profiling", A, []); add("Data Dictionary", A, ["data dictionaries"])

# ---------------- CLOUD
add("AWS", C, ["amazon web services","amazon aws"])
add("EC2", C, []); add("S3", C, []); add("Lambda", C, ["aws lambda"]); add("CloudWatch", C, ["cloud watch"])
add("CloudFront", C, ["cloud front"]); add("CloudFormation", C, ["cloud formation"]); add("RDS", C, [])
add("EBS", C, []); add("SNS", C, []); add("SQS", C, []); add("IAM", C, []); add("Glacier", C, [])
add("Auto Scaling", C, ["autoscaling"]); add("Elastic Beanstalk", C, []); add("Kinesis", C, [])
add("Redshift", C, []); add("EMR", C, []); add("VPC", C, []); add("Route 53", C, [])
add("Azure", C, ["microsoft azure"]); add("GCP", C, ["google cloud"]); add("OpenShift", C, [])
add("PCF", C, ["pivotal cloud foundry"]); add("Google App Engine", C, ["app engine", "gae"]); add("SaaS", C, []); add("PaaS", C, []); add("IaaS", C, [])

# ---------------- SERVIDOR
add("WebLogic", S, ["web logic"]); add("WebSphere", S, ["web sphere"]); add("JBoss", S, [])
add("Tomcat", S, ["apache tomcat"]); add("Apache HTTP Server", S, ["apache http","apache web server","httpd"]); add("IIS", S, []); add("Nginx", S, []); add("Solr", BD, ["apache solr"]); add("NiFi", BD, ["apache nifi"])

# ---------------- FERRAMENTA
add("JIRA", T, []); add("Confluence", T, []); add("Maven", T, ["apache maven"]); add("Gradle", T, [])
add("Ant", T, ["apache ant"]); add("Jenkins", T, []); add("Git", T, ["github","gitlab","bitbucket"])
add("SVN", T, ["subversion"]); add("CVS", T, []); add("ClearCase", T, ["clear case","clearquest"])
add("TFS", T, ["team foundation server"]); add("SoapUI", T, ["soap ui"]); add("Postman", T, [])
add("QTP", T, ["uft","quick test professional"]); add("HP ALM", T, ["quality center","hpalm","alm"])
add("LoadRunner", T, ["load runner"]); add("JMeter", T, []); add("Bugzilla", T, [])
add("Rally", T, ["version one","versionone"]); add("MS Visio", T, ["visio","microsoft visio"])
add("MS Project", T, ["microsoft project","msproject"]); add("MS Excel", T, ["excel","advanced excel"])
add("MS Office", T, ["ms word","powerpoint","ms powerpoint","microsoft office"])
add("SharePoint", T, ["share point"]); add("Tableau", T, []); add("Power BI", T, ["powerbi"])
add("QlikView", T, []); add("Cognos", T, []); add("Business Objects", T, []); add("Crystal Reports", T, [])
add("ERwin", T, ["erwin"]); add("Rational Rose", T, []); add("RequisitePro", T, ["rational requisitepro"])
add("Eclipse", T, []); add("IntelliJ", T, ["intellij idea"]); add("NetBeans", T, [])
add("Visual Studio", T, ["vs code"]); add("Docker", T, []); add("Kubernetes", T, ["k8s"])
add("Ansible", T, []); add("Chef", T, []); add("Puppet", T, []); add("Terraform", T, [])
add("Splunk", T, []); add("Dynatrace", T, []); add("AppDynamics", T, []); add("ServiceNow", T, ["service now"])
add("SnagIt", T, []); add("Balsamiq", T, []); add("Axure", T, []); add("Mantas", T, [])
add("Primavera", T, []); add("Clarity PPM", T, ["clarity","ca ppm"]); add("WinSCP", T, []); add("Putty", T, [])

# ---------------- METODOLOGIA
add("Agile", M, ["agile methodologies","agile methodology"]); add("Scrum", M, ["scrum ceremonies"])
add("Kanban", M, []); add("Waterfall", M, []); add("SAFe", M, ["scaled agile"])
add("RUP", M, ["rational unified process"]); add("TDD", M, ["test driven development"])
add("BDD", M, ["behavior driven development"]); add("DevOps", M, ["dev ops"])
add("SDLC", M, ["software development lifecycle"]); add("STLC", M, [])
add("CI/CD", M, ["ci cd","continuous integration","continuous delivery","continuous deployment"])
add("Lean", M, []); add("Six Sigma", M, ["lean six sigma"]); add("RAD", M, [])
add("JAD", M, ["jad sessions","joint application development"]); add("UAT", M, ["user acceptance testing"])
add("System Integration Testing", M, ["sit testing"]); add("Regression Testing", M, [])
add("Smoke Testing", M, ["sanity testing"]); add("BPM", M, ["business process management"])
add("BPMN", M, []); add("UML", M, []); add("Sprint Planning", M, []); add("Backlog Grooming", M, ["grooming"])
add("Retrospective", M, ["retrospectives"]); add("Daily Scrum", M, ["daily standup","stand up"])
add("PRINCE2", M, []); add("ITIL", M, []); add("Code Review", M, []); add("Pair Programming", M, [])

# ---------------- ARTEFATO BA
add("BRD", A, ["business requirement document","business requirements document"])
add("FRD", A, ["functional requirement document"]); add("SRS", A, ["system requirement specification"])
add("SOW", A, ["statement of work"])
add("RTM", A, ["requirement traceability matrix","requirements traceability matrix","traceability matrix"])
add("Use Case", A, ["use cases"]); add("User Story", A, ["user stories"]); add("Epic", A, ["epics"])
add("Acceptance Criteria", A, []); add("Gap Analysis", A, ["as is","to be"])
add("SWOT Analysis", A, ["swot"]); add("Cost Benefit Analysis", A, ["cost benefit"])
add("Impact Analysis", A, []); add("Root Cause Analysis", A, ["rca"]); add("Risk Analysis", A, [])
add("Feasibility Study", A, []); add("Wireframe", A, ["wireframes","wire frames","mockup","mockups","mock ups","prototype","prototypes"])
add("Test Case", A, ["test cases","test scripts"]); add("Test Plan", A, [])
add("Business Process Modeling", A, ["business process flow","process flow"])
add("Activity Diagram", A, ["activity diagrams"]); add("Sequence Diagram", A, ["sequence diagrams"])
add("Class Diagram", A, ["class diagrams"]); add("State Chart", A, ["state charts","statechart"])
add("ER Diagram", A, ["er diagrams","entity relationship","erd","entity relationship diagram"])
add("Data Flow Diagram", A, ["dfd","data flow diagrams"])
add("Functional Requirements", A, ["functional specification","functional requirement"])
add("Non-Functional Requirements", A, ["non functional requirements","non functional requirement"])
add("Change Request", A, ["change requests","crs"]); add("Defect Tracking", A, ["defect management"])
add("Burndown Chart", A, ["burn down","burndown","burn up"]); add("Velocity Chart", A, ["velocity"])
add("Story Points", A, ["story point"]); add("Estimation", A, ["estimations"]); add("WBS", A, ["work breakdown structure"])
add("RACI", A, []); add("Gantt Chart", A, ["gantt"]); add("Requirement Gathering", A, ["requirements gathering","elicitation"])
add("Stakeholder Analysis", A, [])

# ---------------- GESTAO
add("Project Management", G, []); add("Program Management", G, []); add("Portfolio Management", G, [])
add("Release Management", G, []); add("Change Management", G, []); add("Configuration Management", G, [])
add("Requirements Management", G, ["requirement management"]); add("Vendor Management", G, [])
add("Resource Management", G, []); add("Risk Management", G, []); add("Scope Management", G, [])
add("Budgeting", G, ["budget management","budget planning"]); add("Forecasting", G, [])
add("Capacity Planning", G, []); add("Roadmap", G, ["roadmaps"]); add("Team Management", G, ["people management"])
add("Delivery Management", G, []); add("SLA", G, ["slas"]); add("Status Reporting", G, [])
add("KPI", G, ["kpis"]); add("Business Case", G, []); add("ROI", G, [])
add("Business Intelligence", G, ["bi reporting"]); add("Dashboard", G, ["dashboards"])
add("Data Governance", G, []); add("MDM", G, ["master data management"])

# ---------------- DOMINIO
add("Mortgage", D, ["mortgages","mortgage life cycle"]); add("Insurance", D, ["p&c insurance"])
add("Healthcare", D, ["health care"]); add("Banking", D, ["retail banking","core banking"])
add("Finance", D, ["financial services","financial"]); add("Credit Cards", D, ["credit card"])
add("Investment Banking", D, ["investment"]); add("Brokerage", D, []); add("Trading", D, ["trading systems"])
add("Asset Management", D, ["wealth management"]); add("Retail", D, []); add("E-commerce", D, ["ecommerce","e commerce"])
add("Telecom", D, ["telecommunications"]); add("Supply Chain", D, ["logistics"]); add("Manufacturing", D, [])
add("Automotive", D, []); add("Airlines", D, ["aviation"]); add("Pharmaceutical", D, ["pharma","life sciences","clinical"])
add("Payments", D, ["payment processing"]); add("Underwriting", D, [])
add("Loan Origination", D, ["los","loan origination system"]); add("Claims", D, ["claims processing"])
add("Medicaid", D, []); add("Medicare", D, []); add("HIPAA", D, []); add("HL7", D, [])
add("ICD-10", D, ["icd 10","icd 9"]); add("EDI", D, []); add("AML", D, ["anti money laundering"])
add("KYC", D, []); add("SOX", D, ["sarbanes oxley"]); add("Basel", D, ["basel ii","basel iii"])
add("IFRS", D, []); add("GAAP", D, []); add("ERP", D, []); add("CRM", D, [])
add("SAP", D, []); add("Salesforce", D, []); add("PeopleSoft", D, []); add("Workday", D, [])
add("Mutual Funds", D, ["mutual fund"]); add("Fixed Income", D, []); add("Derivatives", D, [])
add("PCI", D, ["pci dss"]); add("GDPR", D, [])

# ---------------- REGULATORIO
add("TRID", R, []); add("TILA", R, []); add("RESPA", R, []); add("Dodd-Frank", R, ["dodd frank"])
add("Fannie Mae", R, []); add("Freddie Mac", R, []); add("FHA", R, []); add("Ginnie Mae", R, [])
add("LTV", R, ["loan to value"]); add("DTI", R, ["debt to income"]); add("Escrow", R, [])
add("Appraisal", R, []); add("Closing Disclosure", R, ["closing disclosures"]); add("Loan Estimate", R, ["loan estimator"])
add("Compliance", R, ["regulatory compliance"]); add("FINRA", R, []); add("CFPB", R, []); add("FDIC", R, [])
add("OFAC", R, []); add("FATCA", R, []); add("MiFID", R, [])

# ---------------- SOFT SKILL
add("Comunicacao", SS, ["communication","communication skills","written and verbal","verbal communication"])
add("Analitico", SS, ["analytical","analytical skills","analytical thinking"])
add("Resolucao de Problemas", SS, ["problem solving","problem solver"])
add("Lideranca", SS, ["leadership","leadership skills","leading teams"])
add("Interpessoal", SS, ["interpersonal","interpersonal skills"])
add("Negociacao", SS, ["negotiation","negotiation skills"])
add("Apresentacao", SS, ["presentation","presentation skills"])
add("Trabalho em Equipe", SS, ["team player","team work","teamwork","collaboration"])
add("Gestao do Tempo", SS, ["time management","multitasking","multi tasking"])
add("Gestao de Stakeholders", SS, ["stakeholder management","client interaction","client facing"])
add("Mentoria", SS, ["mentoring","coaching","training"])
add("Facilitacao", SS, ["facilitation","facilitating"])



def indice() -> dict[str, tuple[str, str]]:
    """termo de busca -> (canônico, categoria). É o índice-hash do varredor."""
    saida: dict[str, tuple[str, str]] = {}
    for canonico, (categoria, variantes) in CANON.items():
        for termo in variantes:
            saida[termo] = (canonico, categoria)
    return saida


MAX_NGRAMA = 3
