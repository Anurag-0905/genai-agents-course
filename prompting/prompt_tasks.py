"""Session 14 tasks. Each has a deliberately weak prompt, the material you may use, and ACCEPTANCE CHECKS:
plain Python tests that say whether an output is good enough, the way a ticket has acceptance criteria.
Everything is synthetic - fictional people, fake numbers."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from prompt_utils import CheckResult, PromptSpec, chat

# ---------------------------------------------------------------- small reusable checks
def _words(t: str) -> int:
    return len(t.split())


def max_words(n):
    return (f"at most {n} words", lambda t: (_words(t) <= n, f"{_words(t)} words"))


def max_chars(n):
    return (f"at most {n} characters", lambda t: (len(t.strip()) <= n, f"{len(t.strip())} characters"))


def has(text, label=None):
    return (label or f"mentions '{text}'", lambda t: (text.lower() in t.lower(), ""))


def has_none_of(terms, label):
    def run(t):
        found = [x for x in terms if x.lower() in t.lower()]
        return (not found, f"found: {found}" if found else "")
    return (label, run)


def bullet_lines(n):
    def run(t):
        k = sum(bool(re.match(r"^\s*([-*\u2022]|\d+[.)])\s+\S", line)) for line in t.splitlines())
        return (k == n, f"{k} bullet lines")
    return (f"exactly {n} bullet lines", run)


def matches(pattern, label):
    return (label, lambda t: (bool(re.search(pattern, t, re.IGNORECASE)), ""))


def _json(t):
    try:
        data = json.loads(t.strip())
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def json_only():
    return ("reply is a JSON object only (no prose, no code fences)", lambda t: (_json(t) is not None, "" if _json(t) is not None else "did not parse as bare JSON"))


def json_keys(keys):
    return (f"has exactly the keys {sorted(keys)}", lambda t: (_json(t) is not None and set(_json(t)) == set(keys), ""))


def json_value(key, expected, allowed):
    def run(t):
        d = _json(t)
        if d is None or key not in d:
            return (False, "no value")
        v = str(d[key]).lower()
        return (v == expected and v in allowed, f"{key} = {v!r}")
    return (f"{key} is one of {sorted(allowed)} and is '{expected}'", run)


# ---------------------------------------------------------------- the task object
@dataclass
class Task:
    id: str
    title: str
    scenario: str
    weak_prompt: str
    user_input: str
    material: dict = field(default_factory=dict)       # extra facts you may put in your prompt's context
    checks: list = field(default_factory=list)         # [(name, fn)]
    reference: PromptSpec = field(default_factory=PromptSpec)

    def weak_spec(self) -> PromptSpec:
        return PromptSpec(task=self.weak_prompt)

    def acceptance(self) -> list:
        return [name for name, _ in self.checks]


def run_checks(task: Task, text: str) -> list:
    out = []
    for name, fn in task.checks:
        try:
            ok, detail = fn(text)
        except Exception as e:  # noqa: BLE001 - a broken check must not crash a lesson
            ok, detail = False, f"check error: {type(e).__name__}"
        out.append(CheckResult(name, bool(ok), detail))
    return out


def run_task(client, model: str, task: Task, spec: PromptSpec) -> tuple:
    """Run a spec on a task's input; return (output text, check results)."""
    text = chat(client, model, spec.to_messages(task.user_input))["text"]
    return text, run_checks(task, text)


# ---------------------------------------------------------------- demo task (instructor-led, section 2)
DEMO = Task(
    id="DEMO-emi-reminder", title="EMI reminder message",
    scenario="Send a customer a reminder that an EMI is due.",
    weak_prompt="Write a reminder.",
    user_input="Customer: Sneha Iyer\nEMI amount: Rs 18,500\nDue date: 5 November",
    checks=[max_words(40), has("18,500", "includes the amount Rs 18,500"), has("5 November", "includes the due date"),
            has("Sneha", "addresses the customer by name"),
            has_none_of(["penalty", "late fee", "legal"], "does not threaten penalties or legal action")],
    reference=PromptSpec(
        role="You are a customer-service writer for a retail bank, sending friendly payment reminders.",
        task="Write a short, polite EMI reminder message.",
        context="The customer's details are in the input. The tone is warm and respectful: the aim is to help the customer pay on time, not to pressure them.",
        constraints=["Use at most 35 words.", "Address the customer by first name.", "Include the exact amount and the due date.",
                     "Never mention penalties, late fees or legal action."],
        output_format="One plain-text message. No subject line, no markdown."))

# ---------------------------------------------------------------- task 1: credit committee summary
POLICY = """Lending policy (personal loans):
1. Total monthly EMIs (existing plus proposed) must not exceed 50% of monthly income.
2. A credit score of 700 or above is required for approval.
3. Approve if rules 1 and 2 are met and there are no missed payments in the last 24 months.
4. Refer to a senior underwriter if rules 1 and 2 are met but there is exactly one missed payment in the last 24 months.
5. Decline if rule 1 or 2 is not met, or if there are two or more missed payments in the last 24 months."""

TASK1 = Task(
    id="T1-credit-summary", title="Summarise an applicant for a credit committee",
    scenario="A credit committee reads dozens of these a day. They want three lines and a recommendation they can trust.",
    weak_prompt="Summarise this applicant.",
    user_input=("Applicant: Kavya Reddy, 34, software engineer, 6 years with the same employer\n"
                "Monthly income: Rs 1,20,000\nExisting EMIs: Rs 18,000 per month\n"
                "Requested: Rs 10,00,000 personal loan, 60 months at 12% per annum (proposed EMI Rs 22,244)\n"
                "Credit score: 742\nMissed payments in the last 24 months: 1 (30 days late, 14 months ago)"),
    material={"policy": POLICY},
    checks=[max_words(80), bullet_lines(3),
            matches(r"\b(33|34)(\.\d+)?\s*%", "states the total EMI-to-income ratio (about 33-34%)"),
            matches(r"\brefer", "recommends 'refer', as the policy requires")],
    reference=PromptSpec(
        role="You are a credit analyst writing for a credit committee.",
        task="Summarise the applicant and recommend approve, refer or decline.",
        context=POLICY,
        constraints=["Use at most 70 words.",
                     "State the total EMI-to-income ratio as a percentage: (existing EMIs + proposed EMI) divided by monthly income.",
                     "Apply the policy exactly. Do not add opinions that are not in the policy."],
        output_format="Exactly three lines, each starting with '- ': (1) applicant profile, (2) the EMI-to-income ratio, "
                      "(3) 'Recommendation: approve|refer|decline' followed by the policy reason."))

# ---------------------------------------------------------------- task 2: SMS for a declined application
TASK2 = Task(
    id="T2-sms-declined", title="Tell a customer their application was declined, by SMS",
    scenario="The customer reads this on a phone, in a hurry, possibly upset. Some of the facts you hold must never reach them.",
    weak_prompt="Write a message to the customer about their loan.",
    user_input=("Customer: Rohan Mehta\nApplication reference: APP-20931\nOutcome: declined\n"
                "Internal reason (CONFIDENTIAL): internal risk score 612, cutoff 650\n"
                "Customer may reapply after: 90 days\nHelpline: 1800-555-0199"),
    material={"rule": "Internal credit reasons are confidential and must never be shared with customers."},
    checks=[max_chars(300), has("APP-20931", "includes the application reference"), has("1800-555-0199", "includes the helpline number"),
            has("90 days", "mentions the 90-day reapply period"), has("Rohan", "addresses the customer by name"),
            has_none_of(["612", "650", "risk score", "cutoff"], "does NOT reveal the confidential internal reason")],
    reference=PromptSpec(
        role="You are a customer-communications writer at a retail bank.",
        task="Write an SMS telling the customer their loan application was not approved.",
        context="Be kind and clear. Internal credit reasons are confidential and must never be shared with customers. "
                "The customer may reapply after the stated period and can call the helpline.",
        constraints=["Use at most 280 characters.", "Address the customer by first name.",
                     "Include the application reference and the helpline number exactly as given.", "Mention the reapply period.",
                     "Never reveal internal scores, cutoffs or the internal reason."],
        output_format="One plain-text SMS. No subject line, no markdown, no emojis."))

# ---------------------------------------------------------------- task 3: complaint triage as JSON
TASK3 = Task(
    id="T3-complaint-triage", title="Triage a complaint into JSON",
    scenario="The output goes straight into a ticketing system. A single stray sentence breaks the integration.",
    weak_prompt="What is this complaint about?",
    user_input=("My debit card was swallowed by the ATM at the Banjara Hills branch last night. "
                "I am travelling tomorrow morning, please block it and send a new one urgently."),
    material={"categories": "category: card (debit or credit card problems), loan, account (transfers, UPI, statements, balances), "
                            "other (servicing requests such as address or nominee changes). "
                            "urgency: high if money is at risk or the customer is blocked within 24 hours; medium if it needs action "
                            "within a week; low otherwise."},
    checks=[json_only(), json_keys(["category", "urgency"]),
            json_value("category", "card", {"card", "loan", "account", "other"}),
            json_value("urgency", "high", {"low", "medium", "high"})],
    reference=PromptSpec(
        role="You are a triage assistant for a bank's complaints desk.",
        task="Classify the customer's complaint.",
        context="category: card (debit or credit card problems), loan, account (transfers, UPI, statements, balances), "
                "other (servicing requests such as address or nominee changes). "
                "urgency: high if money is at risk or the customer is blocked within 24 hours; medium if it needs action within a week; low otherwise.",
        constraints=["Choose exactly one category and one urgency.", "Do not explain your choice."],
        output_format="A single JSON object with exactly the keys category and urgency, and nothing else: no prose, no markdown code fences."))

# ---------------------------------------------------------------- task 4: loan stipulation notice
TASK4 = Task(
    id="T-loan-stipulation-notice",
    title="Draft a conditional approval document request",
    scenario=(
        "An application has passed initial screening but requires mandatory documentation "
        "to satisfy underwriting stipulations. Draft an SMS/portal notification to the applicant "
        "specifying required items and deadline while keeping internal policy codes confidential."
    ),
    weak_prompt="Tell the applicant we need more documents before we approve the loan.",
    user_input=(
        "Applicant: Sunita Rao. Application Ref: PL-66019. "
        "Loan Amount: INR 8,50,000. Status: CONDITIONAL_APPROVAL. "
        "Required Documents: Latest 3 months salary slips, 6 months primary bank statement. "
        "Submission Portal: portal.securebank.in/upload. Deadline: 5 business days. "
        "Internal Audit Note: High risk employer turnover; manual bank statement analysis required."
    ),
    material={
        "ops_guidelines": (
            "Keep messages under 320 characters. "
            "Include applicant name, application reference PL-66019, required documents, upload link, and 5-day deadline. "
            "Strictly avoid exposing internal notes like 'employer turnover', 'risk', or audit tags."
        )
    },
    checks=[
        max_chars(320),
        has("Sunita", "addresses applicant by name"),
        has("PL-66019", "references application number"),
        has("salary slips", "mentions salary slip requirement"),
        has("bank statement", "mentions bank statement requirement"),
        has("5 business days", "specifies submission deadline"),
        has_none_of(
            ["turnover", "risk", "audit", "manual analysis"],
            "does NOT leak internal underwriting risk flags or operational notes",
        ),
    ],
    reference=PromptSpec(
        role="You are a customer communications agent for a retail bank's lending desk.",
        task="Write a concise SMS alerting the customer to pending loan stipulations.",
        context=(
            "Reference: PL-66019. Applicant: Sunita. "
            "Stipulations: 3 months salary slips and 6 months bank statement via portal.securebank.in/upload. "
            "Deadline: 5 business days. Do not reveal internal risk or audit notes."
        ),
        constraints=[
            "Do not exceed 320 characters.",
            "Do not use internal terms like 'turnover', 'risk', or 'audit'.",
            "Output plain-text message only.",
        ],
        output_format="A single plain-text notification string.",
    ),
)

# ---------------------------------------------------------------- task 5: sms for loan approval
TASK5 = Task(
    id="T-loan-sanction-letter-sms",
    title="Draft a customer loan approval and sanction notification",
    scenario=(
        "The loan has received final credit committee approval. Draft a sanction SMS "
        "containing key offer parameters and acceptance instructions, without disclosing "
        "internal margin spread, broker payout, or underwriter pricing codes."
    ),
    weak_prompt="Tell the user their loan is approved with details: {user_input}",
    user_input=(
        "Customer: Nikhil Verma. Sanction ID: SANC-33910. "
        "Sanctioned Amount: INR 5,00,000. Interest Rate: 10.75% p.a. Tenure: 36 months. "
        "Monthly EMI: INR 16,310. Acceptance Window: 48 hours via mobile banking app. "
        "Internal Desk Memo: Approved with 125 bps risk premium; agent commission 0.50%."
    ),
    material={
        "compliance_rules": (
            "Must state Sanction ID, approved amount, interest rate (10.75%), tenure (36 months), "
            "EMI (INR 16,310), and the 48-hour acceptance window. "
            "Never disclose backend pricing information such as 'bps', 'risk premium', 'commission', or internal spreads. "
            "Length limit: 350 characters."
        )
    },
    checks=[
        max_chars(350),
        has("Nikhil", "greets customer by name"),
        has("SANC-33910", "includes sanction reference ID"),
        has("10.75%", "states the annual interest rate"),
        has("16,310", "cites monthly EMI"),
        has("48 hours", "specifies the acceptance window"),
        has_none_of(
            ["bps", "risk premium", "commission", "desk memo", "spread"],
            "does NOT leak internal bank margins, broker commissions, or risk premiums",
        ),
    ],
    reference=PromptSpec(
        role="You are an automated loan disbursement coordinator.",
        task="Draft a formal loan approval SMS notifying the customer of their sanctioned offer.",
        context=(
            "Sanction details: ID SANC-33910, INR 5,00,000, 10.75% rate, 36 months, EMI INR 16,310. "
            "Action: Accept via mobile app within 48 hours. "
            "Strictly omit risk spreads, premiums, and commissions."
        ),
        constraints=[
            "Keep total length under 350 characters.",
            "Do not include the terms 'bps', 'premium', 'commission', or 'spread'.",
            "Output plain text only.",
        ],
        output_format="A single plain-text SMS string ready for dispatch.",
    ),
)

# ---------------------------------------------------------------- task 6:
TASK6 = Task(
    id="T-loan-overdue-reminder",
    title="Draft a regulatory-compliant soft collections EMI reminder SMS",
    scenario=(
        "An EMI payment is 5 days past due (DPD 5). Draft an early-stage reminder "
        "providing the payment link, amount, and helpline. The message must strictly comply "
        "with Fair Debt Collection practices: zero harassment, zero premature legal threats, "
        "and no defamatory labeling such as 'defaulter'."
    ),
    weak_prompt="Tell the customer to pay their overdue EMI immediately or face consequences: {user_input}",
    user_input=(
        "Borrower: Rajesh Kulkarni. Loan A/C: LA-88301. Overdue EMI: INR 18,450. "
        "Original Due Date: 05 Oct 2026 (5 days overdue). Late Fee: INR 500. "
        "Total Outstanding Due: INR 18,950. Payment Link: pay.bank.com/LA88301. "
        "Collections Desk: 1800-200-9911. "
        "Internal Portfolio Note: Customer has high bounce propensity; flag for field repossession visit if unpaid by DPD 30."
    ),
    material={
        "regulatory_rules": (
            "Keep messages under 300 characters. "
            "Include borrower name, loan account LA-88301, total payable (INR 18,950), payment link, and desk helpline. "
            "Early delinquency rules (DPD < 15): Strictly prohibit coercive, threatening, or defamatory language. "
            "Never use words like 'defaulter', 'legal action', 'police', 'seize', 'repossession', or 'recovery agent'."
        )
    },
    checks=[
        max_chars(300),
        has("Rajesh", "addresses borrower by name"),
        has("LA-88301", "includes loan account reference"),
        has("18,950", "specifies total amount due including late fee"),
        has("pay.bank.com/LA88301", "includes direct payment link"),
        has("1800-200-9911", "provides customer service helpline"),
        has_none_of(
            [
                "defaulter",
                "legal action",
                "police",
                "seize",
                "repossession",
                "recovery agent",
            ],
            "does NOT use aggressive, defamatory, or non-compliant debt collection threats",
        ),
    ],
    reference=PromptSpec(
        role="You are an automated retail loan collections assistant.",
        task="Draft a compliant, respectful early-delinquency EMI reminder SMS.",
        context=(
            "Borrower: Rajesh. Loan: LA-88301. Total due: INR 18,950. "
            "Link: pay.bank.com/LA88301. Support: 1800-200-9911. "
            "Adhere strictly to regulatory fair collection norms: omit aggressive threats, legal warnings, and defamatory words."
        ),
        constraints=[
            "Do not exceed 300 characters.",
            "Never use terms such as 'defaulter', 'legal action', 'police', 'seize', or 'repossession'.",
            "Output plain-text SMS only.",
        ],
        output_format="A single plain-text SMS string ready for transmission.",
    ),
)

TASKS = [TASK1, TASK2, TASK3, TASK4, TASK5, TASK6]

# ---------------------------------------------------------------- zero / one / few-shot: teaching a house convention
LABELS = ["card", "loan", "account", "other"]

CLASSIFY_INSTRUCTION = ("Classify the bank customer's message into exactly one category: card, loan, account or other. "
                        "Reply with that single word only.")

EXAMPLES = [   # kept apart from the test set; each one teaches part of the bank's convention
    ("Net banking transfer of Rs 10,000 shows pending for two days but the money has left my account.", "account"),
    ("I lost my debit card on the train.", "card"),
    ("Please send me a no-dues certificate for my closed home loan.", "loan"),
    ("How do I change my registered mobile number?", "other"),
]

COMPLAINTS_TEST = [   # (message, label under the bank's convention)
    ("My credit card was charged twice for the same restaurant bill.", "card"),
    ("The EMI for my personal loan was deducted but the loan statement still shows it as unpaid.", "loan"),
    ("UPI payment of Rs 4,500 failed but the money was debited from my account.", "account"),
    ("I need to update my address after moving to a new flat.", "other"),
    ("Someone used my card for an online purchase I did not make.", "card"),
    ("The interest rate on my education loan has gone up without any notice.", "loan"),
    ("Please update the nominee details on my savings account.", "other"),
    ("My account statement for September shows a balance that does not match my records.", "account"),
]


def classify_spec(n_examples: int) -> PromptSpec:
    """The same instruction every time; only the number of worked examples changes (0, 1 or 4)."""
    return PromptSpec(task=CLASSIFY_INSTRUCTION, examples=EXAMPLES[:n_examples])


def read_label(reply: str):
    """(label or None, exact). exact means the reply was ONLY the label word, as instructed."""
    cleaned = re.sub(r"[^a-z ]", "", reply.lower()).strip()
    if cleaned in LABELS:
        return cleaned, True
    for lab in LABELS:
        if re.search(rf"\b{lab}\b", cleaned):
            return lab, False
    return None, False


def score_classifier(client, model: str, spec: PromptSpec, items=COMPLAINTS_TEST) -> dict:
    """Run a classifier spec over labelled messages. Returns accuracy and how often the format was obeyed."""
    right = exact = 0
    wrong = []
    for text, truth in items:
        reply = chat(client, model, spec.to_messages(text), max_tokens=300)["text"]
        label, was_exact = read_label(reply)
        right += label == truth
        exact += was_exact
        if label != truth:
            wrong.append((text, truth, label))
    return {"accuracy": right, "exact_format": exact, "n": len(items), "wrong": wrong}