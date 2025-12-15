# Synthetic Job Postings for Validation Testing

**Purpose:** Test Scout's pipeline with representative job posting variations to identify:
1. Input format requirements
2. Noise handling effectiveness
3. Edge case behavior
4. Content extraction quality

---

## Test Case 1: Clean & Structured (Baseline)

**Expected Outcome:** High-quality extraction, good compatibility matching

```text
Senior Python Developer - FinTech Platform

Company: Nordic Financial Technologies
Location: Copenhagen, Denmark (Hybrid)
Employment: Full-time

About the Role:
We are seeking a Senior Python Developer to join our core platform team. You will be responsible for designing and building scalable microservices that power our trading infrastructure.

Requirements:
- 5+ years of professional Python development experience
- Strong experience with FastAPI or Django
- Proficiency with PostgreSQL and Redis
- Experience with Docker and Kubernetes
- Understanding of financial markets is a plus
- Fluent in English (Danish is a plus)

Responsibilities:
- Design and implement high-performance APIs
- Collaborate with data scientists on ML integration
- Mentor junior developers
- Participate in code reviews and architecture discussions
- On-call rotation (1 week per month)

Tech Stack:
- Python 3.11+, FastAPI, SQLAlchemy
- PostgreSQL, Redis, RabbitMQ
- Docker, Kubernetes, AWS
- GitHub Actions, Terraform

Benefits:
- Competitive salary (600-750k DKK)
- Stock options
- 6 weeks vacation
- Pension contribution
- Home office equipment allowance
```

---

## Test Case 2: Noisy with Marketing Fluff

**Expected Outcome:** Rinser should extract core requirements despite noise

```text
🚀 JOIN THE REVOLUTION! 🚀

Are you ready to change the world? Do you wake up every morning thinking about code? Is your IDE your best friend? Then WE WANT YOU!

At InnovateTech Solutions, we're not just building software - we're building DREAMS. We're a family of 200 passionate individuals who believe that technology can solve every problem humanity faces. Our ping pong table is legendary, and our coffee machine makes the best espresso in all of Scandinavia (seriously, we've won awards).

THE OPPORTUNITY OF A LIFETIME:
We're looking for a Software Engineer who bleeds Python and dreams in JavaScript. Someone who can take our already AMAZING platform and make it EVEN MORE AMAZING!!!

What you'll do (when you're not enjoying our unlimited snacks):
• Write code that makes angels sing
• Collaborate with our world-class team of ninjas and rockstars
• Push the boundaries of what's possible
• Attend our monthly team events (last month we went skydiving!)

Must haves (non-negotiable, sorry!):
• Python experience (any amount works, we believe in potential!)
• JavaScript knowledge
• Git (obviously)
• A WINNING attitude 💪

Nice to haves:
• React experience
• Cloud stuff (AWS, GCP, whatever)
• You've built something cool

If InnovateTech sounds like a place where you could thrive and contribute to our mission of making the world a better place through innovative software solutions, we would LOVE to hear from you! Don't be shy - even if you only meet 50% of the requirements, APPLY ANYWAY! We believe in growth mindset! 🌟

PS: Free lunch every day. Yes, really. Every. Single. Day.

Applications: jobs@innovatetech.example.com
```

---

## Test Case 3: Minimal/Bare Requirements

**Expected Outcome:** Should still extract what's available, may flag missing info

```text
Backend Developer

Python, Django, PostgreSQL
3+ years experience
Copenhagen office

Send CV to hr@company.example
```

---

## Test Case 4: Mixed Language (Danish/English)

**Expected Outcome:** Should handle mixed content, extract requirements from both

```text
Softwareudvikler søges - Full Stack Position

Virksomhed: DataSoft ApS
Sted: Aarhus, Danmark

Om stillingen:
Vi søger en erfaren Full Stack Developer til vores voksende team. You will work on our cloud-based analytics platform serving enterprise customers across the Nordics.

Krav:
- 3-5 års erfaring med softwareudvikling
- Strong proficiency in Python and TypeScript
- Experience with React or Vue.js
- Database experience (PostgreSQL, MongoDB)
- God kommunikationsevne på dansk og engelsk

Vi tilbyder:
- Konkurrencedygtig løn
- Flexible working hours
- Pension og sundhedsforsikring
- Årlig konference/kursusbudget

Er du begejstret for at blive en del af DataSoft og bidrage til vores mission om digital transformation? Så vil vi meget gerne høre fra dig!

Ansøgning sendes til: karriere@datasoft.dk
```

---

## Test Case 5: Long & Detailed (Enterprise Style)

**Expected Outcome:** Should extract without truncation, handle complexity

```text
Principal Software Engineer - Enterprise Platform Division

Department: Technology & Innovation
Reports to: VP of Engineering
Location: Copenhagen HQ / Remote (EU timezone)
Job ID: ENG-2024-0847

About Our Company:
GlobalCorp Industries is a Fortune 500 company with operations in 47 countries. Our Enterprise Platform Division builds the internal tools and infrastructure that power our global operations. We process over 50 million transactions daily and maintain 99.99% uptime.

Position Overview:
We are seeking a Principal Software Engineer to lead technical initiatives within our Enterprise Platform team. This is a senior individual contributor role with significant influence on architectural decisions and technical strategy. You will work closely with Staff Engineers, Engineering Managers, and Product leadership to define and execute on our multi-year platform modernization roadmap.

Key Responsibilities:

Technical Leadership:
- Drive architectural decisions for platform services processing 50M+ daily transactions
- Define and enforce engineering standards across 15+ development teams
- Lead technical design reviews and provide mentorship to senior engineers
- Evaluate and introduce new technologies aligned with business objectives

Hands-on Development:
- Design and implement critical platform components
- Write production-quality Python and Go code
- Perform code reviews and ensure code quality standards
- Contribute to open-source projects where applicable

Cross-functional Collaboration:
- Partner with Product Management to translate business requirements into technical specifications
- Collaborate with Security and Compliance teams on platform security posture
- Work with SRE teams to ensure operational excellence
- Present technical proposals to executive leadership

Required Qualifications:

Technical Skills:
- 10+ years of software engineering experience
- 5+ years of experience in distributed systems design
- Expert-level Python programming skills
- Strong experience with Go or Rust
- Deep understanding of event-driven architectures (Kafka, RabbitMQ)
- Extensive experience with cloud platforms (AWS preferred, GCP/Azure acceptable)
- Proficiency with Kubernetes and container orchestration
- Experience with observability tools (Prometheus, Grafana, Datadog)

Architecture & Design:
- Proven track record of designing systems at scale (millions of users/transactions)
- Experience with microservices and service mesh architectures
- Understanding of data modeling and database design (SQL and NoSQL)
- Knowledge of API design principles and patterns (REST, gRPC, GraphQL)

Leadership:
- Experience mentoring senior engineers
- Track record of driving technical initiatives to completion
- Strong written and verbal communication skills
- Ability to influence without direct authority

Preferred Qualifications:
- Experience in financial services or regulated industries
- Contributions to open-source projects
- Conference speaking or technical writing experience
- Master's degree in Computer Science or related field
- Professional certifications (AWS Solutions Architect, Kubernetes, etc.)

Interview Process:
1. Recruiter screen (30 min)
2. Technical phone screen with hiring manager (60 min)
3. System design interview (90 min)
4. Coding interview (60 min)
5. Leadership & collaboration interview (60 min)
6. Executive conversation (30 min)

Compensation & Benefits:
- Base salary: 900,000 - 1,200,000 DKK (based on experience)
- Annual bonus: 15-25% of base
- Stock options / RSUs
- Comprehensive health insurance (family coverage)
- Pension: 10% employer contribution
- 6 weeks paid vacation
- Parental leave: 26 weeks fully paid
- Learning & development budget: 30,000 DKK/year
- Home office setup allowance
- Gym membership
- Company-sponsored meals

Diversity & Inclusion:
GlobalCorp is committed to building diverse teams. We encourage applications from all backgrounds regardless of gender, ethnicity, disability, sexual orientation, or age.

Application Instructions:
Please submit your CV and a brief cover letter explaining why you're interested in this role. Include links to any relevant work (GitHub, technical blog posts, etc.).

Contact: enterprise-careers@globalcorp.example.com
Application Deadline: Rolling basis
Start Date: Q1 2025 (flexible)
```

---

## Test Case 6: Job with Unusual Requirements

**Expected Outcome:** Should handle non-standard items

```text
AI/ML Engineer - Startup Environment

We're a 5-person startup working on computer vision for autonomous drones.

What we need:
- Someone who can ship fast (we deploy daily)
- Python, PyTorch, OpenCV
- Experience with edge deployment (Jetson, RPi)
- Comfortable with ambiguity (startup life!)
- Available for occasional weekend work during launches
- Must love dogs (we have 2 office dogs)
- Willingness to travel (20% international)

Bonus if you have:
- Drone piloting license
- Hardware prototyping skills
- Previous startup experience
- Your own side projects to show us

Anti-requirements (please don't apply if):
- You need detailed specs before starting
- You prefer large, structured teams
- You can't handle rapid pivots

This role is NOT for everyone. We're looking for builders who want equity over stability.

Compensation: Below market salary + significant equity (0.5-1.5%)
Location: On-site only (Malmö, Sweden)
```

---

## Validation Testing Checklist

For each test case, evaluate:

| Aspect | Questions to Answer |
|--------|---------------------|
| **Extraction** | Did Rinser extract job title, company, location? |
| **Requirements** | Were technical requirements properly identified? |
| **Noise Filtering** | Was marketing fluff separated from core content? |
| **Completeness** | Were all sections preserved without truncation? |
| **Language** | How did it handle mixed language content? |
| **Analyzer Match** | Did Analyzer produce reasonable compatibility scores? |
| **Creator Output** | Did generated CV/cover letter use extracted info? |
| **Pipeline Time** | How long did end-to-end processing take? |

---

## Expected Findings

Based on Scout's architecture:

1. **Clean postings** → Should work well out of the box
2. **Noisy postings** → Rinser's sanitization + LLM extraction should filter
3. **Minimal postings** → May produce lower-confidence analysis
4. **Mixed language** → LLM should handle, but monitor quality
5. **Long postings** → Token limits may be a concern for local LLM
6. **Unusual requirements** → Soft skill matching may need tuning

---

*Created: December 15, 2025*
*Purpose: Phase B Validation Testing*
