export type Placement = {
  id: string;
  company: string;
  role: string;
  driveId: string;
  currentRound: string;
  status: "Shortlisted" | "Assessment pending" | "Under review";
  eligibility: string[];
  ctc: string;
  deadline: string;
  deadlineLabel: string;
  applicationUrl: string;
  instructions: string[];
  source: { title: string; version: string; reference: string };
};

export const demoStudent = {
  name: "Aarav Sharma",
  enrollmentNumber: "230611",
  email: "aarav@university.edu",
  university: "Aarohan Demo University",
};

export const studentPlacements: Placement[] = [
  {
    id: "riverbank-ase-2026",
    company: "Riverbank Fintech Labs",
    role: "Associate Software Engineer",
    driveId: "RFL-ASE-2026",
    currentRound: "Round 2 · Technical Assessment",
    status: "Shortlisted",
    eligibility: ["Final-year CSE/IT student", "CGPA 7.5 or above", "No active backlogs"],
    ctc: "₹12 LPA",
    deadline: "2026-09-11T18:00:00+05:30",
    deadlineLabel: "11 Sep 2026 · 6:00 PM",
    applicationUrl: "https://placement.example.edu/drives/RFL-ASE-2026",
    instructions: [
      "Use the assessment link in your placement portal notification.",
      "Keep your university ID and a stable internet connection ready.",
      "Complete the assessment before the deadline; late submissions are not accepted.",
    ],
    source: {
      title: "Riverbank Fintech Labs Approved Placement Notice",
      version: "2026.1",
      reference: "placement://riverbank/RFL-ASE-2026/notice",
    },
  },
  {
    id: "acme-se-2026",
    company: "Acme Cloud Systems",
    role: "Software Engineer",
    driveId: "ACS-SE-2026",
    currentRound: "Round 1 · Online Assessment",
    status: "Assessment pending",
    eligibility: ["Final-year CSE/IT student", "CGPA 7.5 or above", "No active backlogs"],
    ctc: "₹10 LPA",
    deadline: "2026-09-12T17:00:00+05:30",
    deadlineLabel: "12 Sep 2026 · 5:00 PM",
    applicationUrl: "https://placement.example.edu/drives/ACS-SE-2026",
    instructions: [
      "Complete the online assessment in one sitting.",
      "Use a laptop with camera access enabled.",
    ],
    source: {
      title: "Acme Cloud Systems Placement Policy",
      version: "2026.1",
      reference: "placement://acme/ACS-SE-2026/policy",
    },
  },
  {
    id: "northstar-da-2026",
    company: "Northstar Analytics",
    role: "Data Analyst",
    driveId: "NSA-DA-2026",
    currentRound: "Application · Shortlisting",
    status: "Under review",
    eligibility: ["Final-year CSE/IT/ECE student", "CGPA 7.0 or above"],
    ctc: "₹8.5 LPA",
    deadline: "2026-09-15T17:00:00+05:30",
    deadlineLabel: "15 Sep 2026 · 5:00 PM",
    applicationUrl: "https://placement.example.edu/drives/NSA-DA-2026",
    instructions: ["Keep your latest résumé uploaded to the placement portal."],
    source: {
      title: "Northstar Analytics Approved Job Description",
      version: "2026.2",
      reference: "placement://northstar/NSA-DA-2026/jd",
    },
  },
];

export const placementUpdate = {
  title: "Assessment link incident is being reviewed",
  body: "The placement team is checking reports from Riverbank candidates. You will be notified here when a verified update is published.",
  timestamp: "05 Sep 2026 · 9:10 PM",
  affectedStudents: 11,
};
