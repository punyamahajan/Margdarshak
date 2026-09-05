# Margdarshak AI — Product & Development Specification

> **Project Type:** AI-powered Placement Guidance & Coordination Platform  
> **Primary Users:** Final-year students and placement coordinators  
> **Core Technology:** React + FastAPI + Supabase + Agora  
> **Primary Objective:** Reduce repetitive placement queries, improve communication transparency, and help coordinators resolve student issues efficiently.

---

# 1. Project Overview

## 1.1 Problem Statement

Final-year students often face difficulty during placement season because placement information is distributed across multiple channels such as:

- Emails
- PDFs
- Company JDs
- Placement spreadsheets
- University policies
- Messaging groups
- Coordinator calls
- Separate application portals

Students repeatedly ask coordinators questions about:

- Eligibility
- Shortlisting
- Placement drives
- Assessment links
- Deadlines
- Interview rounds
- Application procedures
- Placement policies
- Technical issues

This creates a large amount of repetitive work for placement coordinators.

At the same time, students may receive delayed or inconsistent answers because there is no centralized system that connects their profile with current placement information.

---

# 2. Proposed Solution

## Margdarshak AI

Margdarshak AI is a placement-support platform with two primary perspectives:

1. **Student**
2. **Placement Coordinator / Admin**

The platform combines:

- AI guidance
- Real-time voice interaction through Agora
- Centralized placement knowledge
- Student-specific placement information
- Automated issue detection
- Ticket creation
- Repeated issue clustering
- Coordinator-assisted resolution
- Reusable resolved-issue knowledge

The system should always prefer **verified institutional/company information** over general AI-generated information.

---

# 3. Core Product Philosophy

Margdarshak is not just a chatbot.

It is a **closed-loop placement coordination system**.

```text
Student
   ↓
Ask through AI / Agora
   ↓
Understand issue
   ↓
Search verified knowledge
   ↓
Can the issue be solved?
   ├── YES → Provide answer + source
   │
   └── NO
        ↓
     Clarify issue
        ↓
     Still unresolved?
        ├── NO → Provide answer
        │
        └── YES → Create ticket
                       ↓
                  Admin review
                       ↓
                  Issue clustering
                       ↓
                  Coordinator action
                       ↓
              Agora-assisted response
                       ↓
                  Student update
                       ↓
                    Resolution
                       ↓
              Save resolution as knowledge
                       ↓
          Future students get faster answers
```

---

# 4. System Architecture

```text
┌─────────────────────────────────────────────┐
│                 FRONTEND                    │
│                                             │
│  Student Experience     Admin Experience    │
│        │                       │            │
│        └───────────┬───────────┘            │
│                    ↓                        │
│               FastAPI API                   │
└────────────────────┬────────────────────────┘
                     │
          ┌──────────┴───────────┐
          ↓                      ↓
     Supabase DB             AI Services
          │                      │
          │                      ↓
          │                   Agora
          │                      │
          └──────────┬───────────┘
                     ↓
             Knowledge Engine
                     │
          ┌──────────┼──────────┐
          ↓          ↓          ↓
       Policies   Company    Shortlists
```

---

# PART I — STUDENT EXPERIENCE

# 5. Student Experience Overview

The student experience should be simple, calm, and focused.

The student should not feel like they are using an enterprise dashboard.

The primary goal is:

> **Give students one trusted place to understand their current placement situation and get help.**

---

# 6. Student Identity

For the hackathon MVP, use restricted/demo student accounts.

Each student has:

```text
Name
Enrollment Number
Email ID
```

These three identifiers are used to retrieve student-specific placement information.

Example:

```text
Name: Aarav Sharma
Enrollment Number: 230611
Email: aarav@university.edu
```

---

# 7. Student Home Page

## 7.1 Header

```text
[M] Margdarshak

                                      Aarohan Demo University
```

## 7.2 Hero Section

Use a calm, premium design.

Example:

```text
YOUR STUDENT GUIDANCE COMPANION

Campus questions
can feel
complicated.
Let’s
make them
clearer.
```

Supporting text:

```text
Talk through courses, placements, university processes,
or anything that is worrying you.

Get practical next steps shaped around your student profile.
```

## 7.3 Navigation / Category Pills

```text
Course Discovery
Placement Guidance
Campus Support
```

---

# 8. Student Primary Features

## 8.1 AI Guidance

### Card

```text
AI GUIDANCE

Talk to Margdarshak

Have a private voice conversation.
Your guide remembers the details you share
and builds a live summary.

[ Start a voice conversation → ]

Available now · Usually 5–10 minutes
```

### Purpose

This is the primary Agora interaction.

---

# 9. Agora Student Voice Interaction

When the student clicks:

```text
Start a voice conversation
```

open a dedicated voice interaction screen.

The interface should include:

```text
Margdarshak

Listening...

[ Microphone ]
[ Mute ]
[ End conversation ]
```

The voice interface should:

- Connect to Agora
- Capture student speech
- Support multilingual conversations
- Detect language
- Understand intent
- Ask clarification questions
- Generate a conversation summary
- Search the placement knowledge base
- Decide whether escalation is required

---

# 10. Example Student Conversation

Student:

```text
"Mera Riverbank ka test link open nahi ho raha."
```

The system should understand:

```text
Language:
Hindi

Company:
Riverbank Fintech Labs

Issue:
Assessment link not working

Category:
Technical / Assessment

Urgency:
High
```

The AI should then search:

1. Company information
2. Placement drive
3. Assessment instructions
4. Active incidents
5. Resolved issue knowledge
6. Relevant university policies

---

# 11. Source-Grounded Responses

The system must not invent placement information.

Whenever an answer comes from institutional/company information, show its source.

Example:

```text
You are shortlisted for:

Riverbank Fintech Labs
Associate Software Engineer

Current stage:
Technical Assessment

Deadline:
11 September 2026

Source:
Riverbank Fintech Labs Approved Placement Notice
Version 2026.1
```

---

# 12. Student Placement Cards

The home page should provide a simple overview of current placement processes.

Example:

```text
┌──────────────────────────────────────────┐
│ Riverbank Fintech Labs                  │
│ Associate Software Engineer             │
│                                         │
│ Round 2 · Technical Assessment          │
│                                         │
│ Status: Shortlisted                     │
│ Deadline: 11 Sep 2026                   │
│                                         │
│ View details →                           │
└──────────────────────────────────────────┘
```

Another example:

```text
┌──────────────────────────────────────────┐
│ Acme Cloud Systems                      │
│ Software Engineer                       │
│                                         │
│ Round 1 · Online Assessment             │
│                                         │
│ Status: Assessment Pending              │
│ Deadline: 12 Sep 2026                   │
│                                         │
│ View details →                           │
└──────────────────────────────────────────┘
```

---

# 13. Student Placement Information

Each placement card should expose:

```text
Company
Role
Drive ID
Current Round
Status
Eligibility
CTC
Deadline
Application URL
Instructions
Source
```

---

# 14. Student Eligibility Check

Student can ask:

```text
"Am I eligible for Acme Cloud Systems?"
```

The system should evaluate:

- Student profile
- Company eligibility
- Academic requirements
- Active backlog requirements
- Branch/degree
- Other policy conditions

Example response:

```text
You are eligible for this drive.

Eligibility:
- Final-year CSE/IT student
- CGPA 7.5 or above
- No active backlogs

Source:
Acme Cloud Systems Placement Policy
Version 2026.1
```

---

# 15. Student Shortlisting Check

Student can ask:

```text
"Was I shortlisted for Riverbank?"
```

The system should match:

```text
Name
Enrollment Number
Email
```

against the imported shortlisting dataset.

Example:

```text
You are shortlisted for Riverbank Fintech Labs.

Role:
Associate Software Engineer

Current stage:
Technical Assessment

Source:
Riverbank Fintech Labs Shortlist
```

---

# 16. Student Query Types

The student system should support at least:

```text
Eligibility
Shortlisting
Assessment
Deadline
Interview
Application
Placement Policy
Company Information
Technical Issue
Portal Issue
Document Issue
Other
```

---

# 17. Student Conversation Summary

When an Agora conversation ends, display:

```text
WHAT I KNOW SO FAR

Issue:
Assessment link is not working.

Company:
Riverbank Fintech Labs

Round:
Technical Assessment

Urgency:
High

Language:
Hindi

Current action:
Ticket raised with placement coordinator.
```

---

# 18. Student Ticket Creation

If the AI cannot resolve an issue:

```text
I couldn't confirm a solution from the approved
placement information.

I'll raise this with the placement coordinator.
```

Create a structured ticket.

---

# 19. Student Ticket Data

Each ticket should contain:

```text
Ticket ID
Student ID
Student Name
Enrollment Number
Email
Company
Drive ID
Round
Issue Category
Issue Summary
Conversation Summary
Language
Urgency
Confidence
Status
Created At
Assigned Coordinator
Cluster ID
Resolution
Source
```

---

# 20. Student Repeated Issue Detection

If another student has already reported the same issue, show:

```text
5 other students have reported the same issue.

The placement team is already looking into it.
```

This is intended to reduce student anxiety.

The student should know they are not the only person experiencing the problem.

---

# 21. Student Notifications

After a coordinator resolves an issue:

```text
PLACEMENT UPDATE

The assessment link issue has been resolved.

A new assessment link has been shared with
all affected students.

Updated:
05 Sep 2026 · 21:10
```

---

# 22. Anonymous Peer Support

The student homepage can also provide:

```text
PEER SUPPORT

Chat anonymously

Connect with another student without sharing
your identity.

[ Open anonymous chat → ]

48-hour private bridge · You stay in control
```

This should remain a lightweight MVP feature.

---

# PART II — ADMIN / PLACEMENT COORDINATOR EXPERIENCE

# 23. Admin Experience Overview

The admin interface is designed for placement coordinators.

Its main objective is:

> **Help coordinators identify, prioritize, resolve, and learn from student placement issues.**

The admin interface should be more information-dense than the student interface.

---

# 24. Admin Navigation

Use a left sidebar.

```text
Home
Tickets
Stats
Knowledge
```

---

# 25. Admin Home

The Home page acts as the operational dashboard.

## 25.1 Header

```text
Margdarshak AI

Coordinator workspace for placement support
and peer matching.
```

## 25.2 System Status

```text
Backend connected
```

---

# 26. Admin Overview Metrics

Display:

```text
Open
7

Claimed
3

Waiting
0

Escalated
4

Resolved
1
```

These should be visually prominent.

---

# 27. Admin Priority Alerts

The home page should surface high-priority incidents.

Example:

```text
⚠ HIGH PRIORITY

Assessment link failure

8 students affected

Riverbank Fintech Labs
Technical Assessment

Deadline:
Today, 6:00 PM

[ View issue → ]
```

Priority should increase based on:

```text
Number of affected students
Urgency
Deadline proximity
Repetition
Students blocked from progressing
```

---

# 28. Active Companies

Admin Home should show current drives.

Example:

```text
ACTIVE PLACEMENT DRIVES

Acme Cloud Systems
Software Engineer
Round 1

Riverbank Fintech Labs
Associate Software Engineer
Round 2

Northstar Analytics
Data Analyst
Shortlisting
```

---

# 29. Recent Updates

Show recent operational activity.

Example:

```text
Recent updates

• Riverbank assessment issue reported by 4 students
• Northstar eligibility policy updated
• Acme Cloud Systems shortlist imported
• Riverbank issue resolved
```

---

# 30. Admin Tickets Page

## Header

```text
Tickets

Triage placement questions, keep ownership visible,
and close the loop with students.
```

---

# 31. Ticket Status Board

Use a Kanban structure.

```text
OPEN
CLAIMED
WAITING
ESCALATED
RESOLVED
```

Example:

```text
┌───────────────┐
│ OPEN · 7      │
├───────────────┤
│ Ticket 230611 │
│ Confidence 0% │
│               │
│ No issue      │
│ summary       │
│               │
│ Urgency       │
│ Unknown       │
│               │
│ [View details]│
└───────────────┘
```

---

# 32. Ticket Card

Ticket card should display:

```text
Ticket ID

Confidence

Issue Summary

Urgency
Language
Status

Created At

[ View details ]
```

Example:

```text
230611

Confidence 100%

Assessment link is not working.

Urgency: Urgent
Language: Hindi
Status: Escalated

Created:
05 Sep 2026 · 20:57

[ View details ]
```

---

# 33. Ticket Filters

Provide filters for:

```text
Drive ID
Company
Round
Coordinator ID
Language
Urgency
```

Also:

```text
[ Refresh now ]
```

The ticket page may automatically refresh periodically.

---

# 34. Ticket Detail Panel

When the coordinator opens a ticket, show a side panel.

## Student Information

```text
Student

Name
Enrollment Number
Email
```

## Issue Information

```text
Issue summary
Original student request
Conversation summary
Category
```

## Placement Context

```text
Company
Drive
Role
Round
Deadline
```

## AI Intelligence

```text
Detected language
Confidence
Urgency
Affected students
Cluster
```

## Source

Display:

```text
Policy
Company document
Shortlist
Resolved issue
```

that was used during analysis.

## Actions

```text
Claim
Escalate
Resolve
Dismiss
```

---

# 35. Issue Clustering

This is one of the primary features of the admin system.

Suppose:

```text
Student A → Test link not working
Student B → Test link not working
Student C → Test link not working
Student D → Test link not working
Student E → Test link not working
```

The system should create:

```text
ASSESSMENT LINK ISSUE

5 students affected

Urgency:
High

Status:
Open
```

---

# 36. Repeated Issue Clusters

The Tickets page should contain:

```text
Repeated issue clusters
```

Example:

```text
Assessment link issue · 11 students · Open

Incident update:

[                                              ]

[ Publish update ]        [ Resolve cluster ]
```

---

# 37. Cluster Priority

Cluster priority should be calculated using:

```text
Affected students
Individual ticket urgency
Deadline proximity
Frequency
Whether students are blocked
```

Example:

```text
1 student
Low urgency
Deadline in 10 days
→ Medium

11 students
High urgency
Deadline today
→ Critical
```

---

# 38. Cluster Incident Update

The coordinator can write an update:

```text
The assessment link has been re-issued.
Please use the new link shared through
the placement portal.
```

Then click:

```text
Publish update
```

All affected students receive the same message.

---

# 39. Agora Admin Assistance

The coordinator should be able to use Agora to draft responses.

Button:

```text
Draft response with Agora
```

Coordinator speaks:

```text
"Tell the students that the assessment link
has been shared again and they should complete
it before six PM."
```

AI produces:

```text
UPDATE REGARDING YOUR ASSESSMENT

The assessment link for Riverbank Fintech Labs
has been re-shared.

Please use the new link and complete the assessment
before 6:00 PM today.

If you continue to face an issue, please raise a
new query through Margdarshak.
```

---

# 40. Admin Response Approval

Before publishing:

```text
[ Edit ]
[ Approve & Send ]
[ Cancel ]
```

The coordinator must explicitly approve the response.

---

# 41. Mass Resolution

For an issue cluster:

```text
11 affected students
```

Coordinator:

```text
Open cluster
      ↓
Draft response with Agora
      ↓
Review response
      ↓
Approve
      ↓
Publish to all affected students
      ↓
Resolve cluster
```

All associated tickets should be updated.

---

# 42. Resolution Memory

Every successful resolution should become reusable knowledge.

Example:

```text
Problem:
Riverbank assessment link stopped working.

Resolution:
Company re-issued the assessment link.

Coordinator Response:
Use the newly shared assessment URL.

Source:
Coordinator resolution
05 Sep 2026
```

---

# 43. Future Issue Resolution

A new student later asks:

```text
"Riverbank test link open nahi ho raha."
```

The AI searches resolved issues.

If the previous resolution is still valid:

```text
This issue has already been reported and resolved.

The placement team has re-issued the assessment link.

Please use the new link shared in your placement
notification.

Source:
Resolved placement issue
Riverbank Fintech Labs
```

No duplicate ticket should be created.

---

# 44. Issue Lifecycle

```text
OPEN
  ↓
CLAIMED
  ↓
WAITING / ESCALATED
  ↓
RESOLVED
```

Resolved tickets remain searchable as institutional knowledge.

---

# 45. Admin Stats

The Stats section is lower priority than Tickets and Knowledge.

Display:

```text
Total conversations
Tickets created
Tickets resolved
Average resolution time
Most common issue categories
Most requested companies
Most common languages
Students assisted
```

Use simple charts.

Avoid unnecessary analytics complexity.

---

# 46. Knowledge Management

The Knowledge section manages all information used by Margdarshak AI.

The main sources are:

```text
Placement Policies
Company Information
Placement Drives
Job Descriptions
Shortlisting Spreadsheets
Resolved Issues
```

---

# 47. Knowledge Approval Page

Header:

```text
Knowledge Approval

Review policy versions before they become
student-facing guidance.
```

---

# 48. Create Policy Draft

Form:

```text
Placement Drive
Source Title
Source Reference
Version Label
Eligibility
Salary / CTC
Application Deadline
Application URL
Instructions
```

Example:

```text
Placement Drive:
Acme Cloud Systems

Source Title:
Acme Cloud Systems Placement Notice

Source Reference:
manual://coordinator-entry

Version:
2026.1
```

Action:

```text
[ Save as Draft ]
```

---

# 49. Policy Lifecycle

Knowledge items should support:

```text
DRAFT
PUBLISHED
EXPIRED
```

Example:

```text
demo-approved-2026.1

Status:
Published

Source:
Riverbank Fintech Labs Approved Placement Notice

Version:
2026.1

[ Expire ]
```

---

# 50. CSV / XLSX Ingestion

Admin should be able to import company shortlisting data.

Input:

```text
Import for drive
Import title
Source reference
Version prefix

[ Upload CSV/XLSX ]
```

---

# 51. Shortlist Spreadsheet Structure

Minimum recommended columns:

```text
name
enrollment_number
email
company
drive_id
shortlisted
role
round
```

---

# 52. Import Workflow

```text
Upload file
    ↓
Parse file
    ↓
Validate columns
    ↓
Preview records
    ↓
Show errors
    ↓
Admin confirms
    ↓
Import
    ↓
Knowledge becomes available
```

---

# 53. Knowledge Library

Show all uploaded knowledge.

Recommended columns:

```text
Document
Type
Company
Version
Status
Source
Last Updated
```

This gives the coordinator visibility into what the AI is actually using.

---

# 54. Knowledge Retrieval Priority

When answering student queries:

```text
1. Active resolved issue
2. Company / drive information
3. Published placement policy
4. Student shortlisting record
5. Other approved institutional guidance
```

Expired knowledge must not be used for current authoritative answers.

---

# 55. Student + Admin Interaction Model

The complete system should work as follows:

```text
                    STUDENT
                       │
                       ↓
                Start conversation
                       │
                       ↓
                    AGORA
                       │
                       ↓
              AI understands issue
                       │
                       ↓
             Search knowledge base
                       │
                ┌──────┴──────┐
                │             │
              FOUND        NOT FOUND
                │             │
                ↓             ↓
        Answer + source    Clarify
                              │
                              ↓
                       Still unresolved?
                         /           \
                       YES            NO
                        │              │
                        ↓              ↓
                     Ticket         Answer
                        │
                        ↓
                Issue clustering
                        │
                        ↓
                     ADMIN
                        │
                        ↓
                 Coordinator action
                        │
                        ↓
                  AGORA drafting
                        │
                        ↓
                   Admin approval
                        │
                        ↓
                 Student notification
                        │
                        ↓
                     RESOLVE
                        │
                        ↓
                Save resolution
                        │
                        ↓
                Reusable knowledge
```

---

# 56. Database Structure

Use Supabase PostgreSQL.

Recommended tables:

```text
students
coordinators
companies
drives
shortlist_records
knowledge_documents
knowledge_versions
tickets
ticket_clusters
ticket_messages
conversations
conversation_summaries
resolutions
notifications
```

---

# 57. Database Relationships

```text
Student
 ├── Conversations
 ├── Tickets
 └── Shortlist Records

Company
 └── Drives

Drive
 ├── Shortlist Records
 ├── Tickets
 └── Knowledge

Ticket
 ├── Student
 ├── Drive
 ├── Cluster
 └── Resolution
```

---

# 58. Backend

Use:

```text
Python
FastAPI
Supabase
```

Suggested service structure:

```text
backend/

├── main.py
├── api/
│   ├── students.py
│   ├── drives.py
│   ├── tickets.py
│   ├── clusters.py
│   ├── knowledge.py
│   └── stats.py
│
├── services/
│   ├── ai_service.py
│   ├── knowledge_service.py
│   ├── ticket_service.py
│   ├── clustering_service.py
│   ├── notification_service.py
│   └── agora_service.py
│
├── models/
├── schemas/
├── database/
└── utils/
```

---

# 59. Suggested API

```text
GET    /students/{id}
GET    /students/{id}/placements

GET    /companies
GET    /drives
GET    /drives/{id}

POST   /conversations
GET    /conversations/{id}

POST   /conversations/{id}/summary

POST   /tickets
GET    /tickets
GET    /tickets/{id}
PATCH  /tickets/{id}

GET    /ticket-clusters
GET    /ticket-clusters/{id}

POST   /ticket-clusters/{id}/resolve
POST   /ticket-clusters/{id}/publish-update
POST   /ticket-clusters/{id}/draft-response

POST   /knowledge/policy
POST   /knowledge/import
GET    /knowledge
PATCH  /knowledge/{id}

GET    /stats
```

---

# 60. AI Service Responsibilities

The AI service should support:

```text
Language detection
Intent detection
Issue classification
Conversation summarization
Knowledge retrieval
Response generation
Urgency detection
Confidence estimation
Response drafting
```

The AI should not be responsible for storing business data directly.

Business logic belongs in the backend.

---

# 61. Confidence Rules

Example:

```text
Exact approved policy match
→ 95–100% confidence

Strong company/drive match
→ 85–95%

Partial information
→ 60–85%

No reliable information
→ Low confidence
```

When confidence is low:

```text
Do not invent an answer.

Ask clarification or escalate.
```

---

# 62. Security

Use environment variables:

```env
SUPABASE_URL=
SUPABASE_KEY=

AGORA_APP_ID=
AGORA_APP_CERTIFICATE=

AI_API_KEY=
```

Never expose private keys in frontend code.

Student information should not be publicly accessible.

Anonymous peer conversations should not reveal student identity.

---

# 63. Frontend Structure

Suggested structure:

```text
frontend/

├── src/
│
├── pages/
│   ├── Landing.tsx
│   │
│   ├── student/
│   │   ├── StudentHome.tsx
│   │   ├── PlacementDetails.tsx
│   │   ├── Conversation.tsx
│   │   └── AnonymousChat.tsx
│   │
│   └── admin/
│       ├── AdminHome.tsx
│       ├── Tickets.tsx
│       ├── Stats.tsx
│       └── Knowledge.tsx
│
├── components/
│   ├── student/
│   └── admin/
│
├── services/
│   ├── api.ts
│   └── agora.ts
│
└── types/
```

---

# 64. Reusable Components

## Student Components

```text
StudentHeader
PlacementCard
GuidanceCard
PeerSupportCard
VoiceConversation
ConversationSummary
SourceBadge
NotificationCard
```

## Admin Components

```text
AdminSidebar
StatsCard
TicketBoard
TicketCard
TicketDetails
ClusterCard
PriorityAlert
KnowledgeCard
PolicyForm
ImportForm
```

---

# 65. Design System

## Student

Use:

```text
Background:
Warm off-white / cream

Primary:
Muted sage / olive

Text:
Dark charcoal

Typography:
Elegant serif headings
Clean sans-serif body text

Cards:
Rounded
Subtle borders
Soft shadows

Layout:
Spacious
Minimal
Calm
```

## Admin

Use:

```text
Background:
Light grey / blue-grey

Primary:
Dark charcoal

Accent:
Muted green

Cards:
Simple borders
Minimal shadows

Layout:
Compact
Operational
Information-dense
```

---

# 66. Important UX Rules

## Student

Do:

- Keep information simple.
- Show only relevant placement information.
- Use clear language.
- Show source of important answers.
- Make voice interaction prominent.

Do not:

- Create a cluttered enterprise dashboard.
- Show unnecessary statistics.
- Overload the student with operational information.

## Admin

Do:

- Prioritize urgent issues.
- Make affected student count visible.
- Allow fast filtering.
- Allow bulk resolution.
- Make ownership visible.
- Show knowledge sources.

---

# 67. Error States

Avoid exposing raw errors such as:

```text
Failed to fetch
```

Instead use:

```text
We couldn't load the conversation summary.

Your conversation has been saved.
Please try again.
```

Other required states:

```text
Agora connection failed
AI unavailable
Knowledge unavailable
Invalid CSV
Missing required fields
Expired policy
Empty ticket state
Empty knowledge state
```

---

# 68. Loading States

Examples:

```text
Connecting to Margdarshak...

Loading placement information...

Searching approved placement information...

Analyzing your request...

Saving conversation...

Creating support ticket...
```

---

# 69. Demo Data

Seed the database with realistic demo data.

## Companies

```text
Acme Cloud Systems
Riverbank Fintech Labs
Northstar Analytics
```

## Students

At least:

```text
5–10 students
```

Each with:

```text
Name
Enrollment
Email
```

---

# 70. Demo Placement Drives

Example:

```text
Riverbank Fintech Labs
Role:
Associate Software Engineer

Round:
Technical Assessment

Deadline:
11 September 2026
```

---

# 71. Demo Policies

Example:

```text
Eligibility:

Final-year CSE/IT students
CGPA 7.5 or above
No active backlogs
```

---

# 72. Demo Tickets

Seed tickets across:

```text
Open
Claimed
Waiting
Escalated
Resolved
```

---

# 73. Demo Cluster

Create:

```text
Assessment link issue

11 students affected

Urgency:
High
```

---

# 74. Demo Resolved Issue

Create a resolved issue such as:

```text
Problem:
Assessment link not working

Resolution:
Company re-issued the assessment link.

Response:
Use the newly shared link from the placement portal.
```

This allows the system to demonstrate knowledge reuse.

---

# 75. Primary Hackathon Demo Flow

The complete demonstration should follow this sequence.

## Step 1 — Student

Student logs into Margdarshak.

```text
Student Home
```

## Step 2 — Placement Overview

Student sees:

```text
Riverbank Fintech Labs
Technical Assessment
Shortlisted
```

## Step 3 — Start Agora

Student clicks:

```text
Start a voice conversation
```

## Step 4 — Student Reports Problem

Student says:

```text
"Mera Riverbank ka test link open nahi ho raha."
```

## Step 5 — AI Understanding

System identifies:

```text
Company:
Riverbank Fintech Labs

Issue:
Assessment link

Language:
Hindi

Urgency:
High
```

## Step 6 — Knowledge Search

System checks:

```text
Company information
Assessment instructions
Current incidents
Resolved issues
Placement policies
```

## Step 7 — Escalation

No current solution is found.

Ticket is created.

## Step 8 — Admin Dashboard

Admin immediately sees:

```text
New ticket

Assessment link issue
Urgency: High
Language: Hindi
```

## Step 9 — Clustering

Admin sees:

```text
11 students affected
```

## Step 10 — Admin Opens Cluster

Admin reviews:

```text
Issue
Affected students
Deadline
Conversation summaries
Urgency
```

## Step 11 — Agora Admin Drafting

Admin clicks:

```text
Draft response with Agora
```

and verbally explains the resolution.

## Step 12 — AI Draft

AI produces a professional response.

## Step 13 — Approval

Admin clicks:

```text
Approve & Send
```

## Step 14 — Student Notification

All affected students receive the same approved update.

## Step 15 — Resolution

Tickets become:

```text
Resolved
```

## Step 16 — Knowledge Reuse

Resolution is stored.

## Step 17 — New Student

Another student reports the same issue.

The AI retrieves the previous resolution.

No duplicate ticket is necessary.

---

# 76. MVP Feature Priority

## P0 — Must Have

```text
Student home
Student placement cards
Agora student voice
AI query handling
Knowledge retrieval
Source-grounded responses
Ticket creation
Admin Home
Admin Tickets
Ticket details
Issue clustering
Admin Agora response drafting
Mass resolution
Resolved issue knowledge reuse
```

## P1 — Important

```text
Policy ingestion
CSV/XLSX ingestion
Knowledge approval
Student notifications
Admin filters
Priority alerts
Stats
```

## P2 — Nice to Have

```text
Anonymous peer chat
Advanced analytics
Advanced authentication
Complex role permissions
Advanced recommendation systems
```

---

# 77. Project Success Criteria

## Student

```text
Student logs in
       ↓
Sees placement information
       ↓
Starts Agora
       ↓
Asks placement question
       ↓
Receives verified answer
```

## Escalation

```text
Unresolved query
       ↓
Clarification
       ↓
Ticket created
```

## Admin

```text
Ticket appears
       ↓
Coordinator opens ticket
       ↓
Claims / escalates / resolves
```

## Clustering

```text
Repeated issue
       ↓
Issue cluster
       ↓
Affected student count visible
```

## Agora Resolution

```text
Admin voice input
       ↓
AI-generated response
       ↓
Coordinator approval
       ↓
Mass student notification
```

## Knowledge Reuse

```text
Resolved issue
       ↓
Stored as reusable knowledge
       ↓
Future issue
       ↓
Automatic resolution
```

---

# 78. Final Product Positioning

## Margdarshak AI

> **A trusted AI placement coordination layer between students and university placement teams.**

The system combines:

```text
AI
+
Agora
+
Placement Knowledge
+
Student Context
+
Ticket Management
+
Issue Clustering
+
Coordinator Workflow
+
Institutional Memory
```

The ultimate objective is to:

```text
Reduce repetitive communication
        +
Give students trustworthy answers
        +
Surface important issues early
        +
Help coordinators resolve issues faster
        +
Turn solved problems into reusable knowledge
```

---

# 79. Final Development Principle

The application should always follow this rule:

```text
ANSWER WHEN YOU KNOW
ASK WHEN YOU NEED CLARITY
ESCALATE WHEN YOU CANNOT RESOLVE
CLUSTER WHEN MANY STUDENTS ARE AFFECTED
RESOLVE ONCE
REMEMBER THE RESOLUTION
```

This should be the central product logic of Margdarshak AI.
