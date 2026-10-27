# ATLANTECH — Decisions, Conflicts and Open Points

This file lists every decision that must be closed before implementation, every conflict between the source documents, and every open point. Each item has a fixed ID from `DEC-01` to `DEC-56`.

- **Closing task:** has the same ID as the item and belongs to the owner team. It sits in the sprint where the first task that needs the decision starts, and is closed at that sprint's FRR or earlier.
- **Status:** `Open` needs a decision by its closing sprint. `Closed` is already settled and kept for reference.
- **Recommendation:** my proposal based on the documents. The final decision is written in the "Decision" row when the Leads Council closes the item.
- **القصة:** under each item, a short story in Arabic that explains where the problem is.

## Summary

| ID | Item | Owner | Status | Close by |
| --- | --- | --- | --- | --- |
| DEC-01 | AI completion signal | Backend Team | Open | Sprint 1 |
| DEC-02 | Who writes status transitions, history, audit and run rows | Backend Team | Open | Sprint 1 |
| DEC-03 | Location of the shared validation rule sets (override, yard adjustment, BAPLIE correction, window re-check) | AI Team | Open | Sprint 1 |
| DEC-04 | Job envelope, versioning, retries and stale-run timeout | AI Team | Open | Sprint 1 |
| DEC-05 | SSE source for the dashboard | Backend Team | Open | Sprint 1 |
| DEC-06 | Joint solve scope: which requests may change per trigger | AI Team | Open | Sprint 1 |
| DEC-07 | Storing a NO_FEASIBLE_WINDOW result | AI Team | Open | Sprint 5 |
| DEC-08 | Database read source and worker privileges | Backend Team | Open | Sprint 1 |
| DEC-09 | Where deviation thresholds live | Backend Team | Open | Sprint 6 |
| DEC-10 | Scope of the AI FastAPI service | AI Team | Open | Sprint 1 |
| DEC-11 | Redis persistence | Backend Team | Open | Sprint 3 |
| DEC-12 | AI `port_setting` keys | AI Team | Open | Sprint 1 |
| DEC-13 | Who keeps the OpenAPI file current | Backend Team | Open | Sprint 1 |
| DEC-14 | C-01 · Part 1 run | AI Team | Open | Sprint 1 |
| DEC-15 | C-02 · Part 2 solve | AI Team | Open | Sprint 1 |
| DEC-16 | C-03 · Yard placement | AI Team | Open | Sprint 1 |
| DEC-17 | C-04 · BAPLIE parse | AI Team | Open | Sprint 1 |
| DEC-18 | C-05 · Validation | AI Team | Open | Sprint 1 |
| DEC-19 | C-06 · Completion message | AI Team | Open | Sprint 1 |
| DEC-20 | Tug-count formula | AI Team | Open | Sprint 2 |
| DEC-21 | Phase 1 delay-risk rule | AI Team | Open | Sprint 3 |
| DEC-22 | Financial-impact data in ranking | AI Team | Open | Sprint 4 |
| DEC-23 | Objective terms, weights and number of options | AI Team | Open | Sprint 1 |
| DEC-24 | Part 1 settings: horizon, time step, minimum window, slot | AI Team | Open | Sprint 4 |
| DEC-25 | Uncertainty margin and window confidence | AI Team | Open | Sprint 3 |
| DEC-26 | Weather and marine providers | AI Team | Open | Sprint 4 |
| DEC-27 | Tidal constants source, datum and reference | AI Team | Open | Sprint 4 |
| DEC-28 | Definition of moves | AI Team | Open | Sprint 3 |
| DEC-29 | Yard recommendation method, objective and confidence | AI Team | Open | Sprint 3 |
| DEC-30 | Numeric thresholds register | AI Team | Open | Sprint 2 |
| DEC-31 | Part 3 scheduling host | AI Team | Open | Sprint 6 |
| DEC-32 | Availability semantics for pilots and tug masters | AI Team | Open | Sprint 3 |
| DEC-33 | Manual-planning baseline | AI Team | Open | Sprint 7 |
| DEC-34 | Building A4 rules on synthetic data | AI Team | Open | Sprint 3 |
| DEC-35 | Sign-in identifier | Backend Team | Open | Sprint 1 |
| DEC-36 | One role per user vs role history | Backend Team | Open | Sprint 2 |
| DEC-37 | "Reject with reason" on P-44 and P-47 | Backend Team | Open | Sprint 6 |
| DEC-38 | Where to activate the tide constituent set | UI/UX Team | Open | Sprint 3 |
| DEC-39 | CT Supervisor status list | Backend Team | Open | Sprint 6 |
| DEC-40 | Mobile Acknowledge event type and payload | Backend Team | Open | Sprint 6 |
| DEC-41 | Automatic sync right after saving an event while online | Mobile Team | Open | Sprint 4 |
| DEC-42 | Staff pages on the tablet and a provisioning screen | Leads Council | Open | Sprint 2 |
| DEC-43 | Recommendation confidence field on P-38 | AI Team | Open | Sprint 6 |
| DEC-44 | Storing the clock-skew review note | Backend Team | Open | Sprint 6 |
| DEC-45 | Display time zone | Frontend Team | Open | Sprint 1 |
| DEC-46 | Supported browsers and viewports | Frontend Team | Open | Sprint 1 |
| DEC-47 | Backend environment for development and testing | Backend Team | Open | Sprint 2 |
| DEC-48 | Field roles on the web | Leads Council | Open | Sprint 2 |
| DEC-49 | Status and error colours and the icon set | UI/UX Team | Closed | — |
| DEC-50 | BAPLIE correction and withdraw | Leads Council | Closed | — |
| DEC-51 | Shared berths | Leads Council | Closed | — |
| DEC-52 | Boat management (P-61) | Leads Council | Closed | — |
| DEC-53 | Screens baseline | Leads Council | Closed | — |
| DEC-54 | Licence, SaaS and READ_ONLY in the task files | Leads Council | Closed | — |
| DEC-55 | TIMING and NCT recommendation producers | Leads Council | Closed | — |
| DEC-56 | SaaS API location and licence signing key | Leads Council | Closed | — |

## Backend–AI integration decisions

### DEC-01 · AI completion signal

| | |
| --- | --- |
| Source | D-01 · OD-01 · AIBD-010 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-01 · Sprint 1 |
| Affects | P3-I3 · AI-011 · CT-14 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الموظف داس "موافقة الجمارك"، والـ AI حسب نوافذ الدخول وكتبها في الـ database. بس الـ Laravel مايعرفش إن الـ AI خلص، فالشاشة فاضلة واقفة على "جاري الحساب" لحد ما حد يعمل refresh. محتاجين طريقة الـ AI يقول بيها للـ Backend "أنا خلصت".

</div>

**Topic.** Laravel must learn that a worker finished so it can send SSE and notifications within 5 seconds of the commit. No mechanism is documented.

**Options:**

1. After committing, the worker pushes a JSON message (RPUSH) to a list named `queue:ai-results`; the Backend runs a consumer as a supervised artisan command.
2. A Backend poller reads the run tables at intervals (slower).
3. MySQL change capture (new infrastructure).

**Recommendation.** Option 1 with a poller as a safety net. Both teams agree, and it needs no new infrastructure because Redis is already there.

### DEC-02 · Who writes status transitions, history, audit and run rows

| | |
| --- | --- |
| Source | D-02 · OD-02 · AIBD-011 · AIBD-013 · AIBD-025 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-02 · Sprint 1 |
| Affects | P3-I2 · P4-K1 · AI-058 |
| Decision | ______ |

<div dir="rtl">

**القصة.** لو الـ AI والـ Backend الاتنين بيغيّروا حالة الطلب، ممكن الاتنين يكتبوا في نفس اللحظة والحالة تبوظ، أو الـ history يتسجل مرتين، أو يتسجل من غير audit. لازم يبقى فيه "صاحب" واحد بس لحالة الطلب.

</div>

**Topic.** Request status (SM-4), its history and its audit need a single writer. `solver_run.solver_version` is mandatory and only the worker knows it.

**Options:**

1. The Backend writes every request transition, history row and audit entry, and creates the run row as QUEUED before enqueueing. The AI writes run progress and result tables only.
2. The AI writes everything in its result transaction.

**Recommendation.** Option 1 (agreed). The Backend writes `solver_version` from `port_setting`; the worker overwrites it if different.

### DEC-03 · Location of the shared validation rule sets (override, yard adjustment, BAPLIE correction, window re-check)

| | |
| --- | --- |
| Source | D-03 · OD-03 · AIBD-008 · AIBD-034 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-03 · Sprint 1 |
| Affects | P4-K4 · P6-P3 · P3-H6 · AI-060 · AI-067 · AI-F03 · CT-13 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ AI اقترح الرصيف B12 للسفينة. الموظف عمل override وغيّره لـ B7، بس B7 أقل عمق من الغاطس بتاع السفينة. القاعدة اللي بتمنع ده مكتوبة في كود الـ AI بس. لو الـ Backend كتب نسخة تانية من القاعدة، النسختين ممكن يختلفوا مع الوقت. ولو سأل الـ AI في الخلفية، الموظف هيستنى. لازم نحدد القواعد دي هتعيش فين.

</div>

**Topic.** The same hard rules must apply in two places: when the AI generates a result and when a user edits it. The teams disagree: the AI wants a background job, the Backend wants the check inside Laravel.

**Options:**

1. Async job on the worker (C-05): one Python implementation; the user waits for the result over SSE.
2. A second copy of the rules in Laravel with shared test vectors: instant answer, but two codebases that must stay identical.
3. A synchronous endpoint on the AI FastAPI service: Laravel calls it and waits; the rules are written once in Python.

**Recommendation.** Option 3 for override and yard adjustment: an instant answer (422 with the broken constraint) and a single implementation. BAPLIE correction stays async on `queue:edi` because it is heavy. If FastAPI is unreachable the Backend refuses the change (fail closed). The window re-check stays in Laravel: it confirms the proposal is the latest and the forecast run is still the newest.

### DEC-04 · Job envelope, versioning, retries and stale-run timeout

| | |
| --- | --- |
| Source | D-04 · OD-22 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-04 · Sprint 1 |
| Affects | P3-I1 · AI-011 · CT-08 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Laravel بيحط الـ jobs في Redis بصيغة PHP، والـ worker مكتوب Python ومش هيعرف يقراها. ولو الـ worker وقع وهو شغال، الـ run هيفضل "RUNNING" للأبد. محتاجين نتفق على شكل الرسالة، ونعيد المحاولة كام مرة، وإمتى نعتبر الـ run مات.

</div>

**Topic.** The default Laravel queue format serialises PHP classes that Python cannot read.

**Options:**

1. JSON envelope pushed with RPUSH onto the documented queue name, `contract_version = "1.0"`.
2. Laravel job classes with a decoder in Python.

**Recommendation.** Option 1 (agreed), with unprefixed key names. Retries: Part 1 up to 3 (documented), others once. A run left RUNNING longer than `run_stale_after_seconds` is marked FAILED.

### DEC-05 · SSE source for the dashboard

| | |
| --- | --- |
| Source | D-06 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-05 · Sprint 1 |
| Affects | P3-I4 · FE-033 · CT-05 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ dashboard لازم يتحدث لحظيًا من غير refresh. محدش اتفق الأحداث دي بتطلع منين وبأي شكل. فالـ Frontend مش هيعرف يبني الـ SSE client، والـ Backend مش هيعرف يبني الـ endpoint.

</div>

**Topic.** The AI documents do not say what feeds the SSE.

**Options:**

1. A Laravel streamed endpoint reading from a short-lived events store (Redis); Reverb for mobile only.
2. Reverb for both web and mobile.

**Recommendation.** Option 1 (Backend position): `GET /api/v1/events` filtered by role and terminal, with `Last-Event-ID` catch-up.

### DEC-06 · Joint solve scope: which requests may change per trigger

| | |
| --- | --- |
| Source | D-07 · OD-08 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-06 · Sprint 1 |
| Affects | AI-050 · AI-055 · P4-K1 · P4-K5 |
| Decision | ______ |

<div dir="rtl">

**القصة.** سفينة جديدة وصلت والـ AI هيحسب لها مكان. هل مسموح يحرّك السفن التانية اللي لسه توصياتها مستنية موافقة؟ ولا يحطها بس في الأماكن الفاضية؟ ولو حرّك سفينة، التوصية القديمة بتاعتها تتلغي؟

</div>

**Topic.** CP-SAT solves for the whole port, so we must define what is fixed and what is variable.

**Options:**

1. Confirmed plans are fixed; pending requests and the trigger request are variable.
2. Only the trigger request is variable.

**Recommendation.** Option 1 (agreed). It defines which pending versions become REPLACED.

### DEC-07 · Storing a NO_FEASIBLE_WINDOW result

| | |
| --- | --- |
| Source | D-08 · OD-10 · PS-01 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-07 · Sprint 5 |
| Affects | P4-J1 · AI-048 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الطقس وحش طول الأيام الجاية، والـ AI مالقاش أي نافذة دخول. لازم يسجل "مفيش نافذة" ومعاها الفترات الممنوعة وسببها. بس الـ schema مايسمحش بفترة ممنوعة من غير proposal.

</div>

**Topic.** `blocked_period.proposal_id` is mandatory, so a proposal must exist even when no window exists.

**Options:**

1. A proposal with no windows, linked from the run (schema note change only).
2. An unlinked proposal found by request and time.

**Recommendation.** Option 1 (agreed).

### DEC-08 · Database read source and worker privileges

| | |
| --- | --- |
| Source | D-09 · OD-21 · AIBD-028 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-08 · Sprint 1 |
| Affects | P3-I5 · AI-013 |
| Decision | ______ |

<div dir="rtl">

**القصة.** لو كل الـ workers داخلين على الـ database بنفس الحساب بكل الصلاحيات، أي bug في الـ parser ممكن يمسح جدول الخطط. ولو قرأوا من نسخة متأخرة، ممكن يحسبوا على رصيف اتحجز من ثواني.

</div>

**Topic.** Each worker must read port state and write only its own results.

**Options:**

1. Read from the primary, one account per worker with limited rights, `audit_log` INSERT/SELECT only.
2. Read from the replica and tolerate lag.

**Recommendation.** Option 1 (agreed); the Backend writes the grants script.

### DEC-09 · Where deviation thresholds live

| | |
| --- | --- |
| Source | D-10 · OD-16 (part) · AIBD-020 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-09 · Sprint 6 |
| Affects | P5-O6 · P5-O7 |
| Decision | ______ |

<div dir="rtl">

**القصة.** القاطرة اتأخرت 10 دقايق. هل ده تأخير مهم يستاهل إعادة تخطيط، ولا عادي؟ الحد ده لازم الـ Port Admin يغيّره، بس مفيش مكان في الـ database نحفظه فيه.

</div>

**Topic.** The thresholds that make a delay "significant" per operation type have no place in the schema.

**Options:**

1. `port_setting` keys per component type.
2. A new table.

**Recommendation.** Option 1 (agreed). Edited from P-62.

### DEC-10 · Scope of the AI FastAPI service

| | |
| --- | --- |
| Source | New decision |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-10 · Sprint 1 |
| Affects | AI-F01 · AI-F02 · AI-F03 · CT-16 |
| Decision | ______ |

<div dir="rtl">

**القصة.** اتقرر إن الـ AI هيبقى ليه APIs بـ FastAPI، بس كل المستندات مبنية على إن الكلام بين الـ Backend والـ AI عن طريق Redis بس. لو ماحددناش الـ FastAPI مسؤول عن إيه، كل تيم هيفترض حاجة. ممكن نلاقي نفس الشغل متعمل مرتين، أو حل CP-SAT واخد ثواني مستني جوه HTTP request.

</div>

**Topic.** The AI will expose APIs with FastAPI. The documents say Laravel and Python talk only through Redis, so the role of FastAPI must be set.

**Options:**

1. FastAPI is an internal API layer on top of the workers: health and readiness of each worker, synchronous validation (DEC-03), and run status for diagnosis. Heavy work (Part 1, Part 2, parsing, yard) stays on the queues.
2. FastAPI replaces the queues and all work becomes HTTP.

**Recommendation.** Option 1. FastAPI is internal to the port server and is not exposed to the web or mobile app. Laravel is its only client, authenticated with a service token header (`X-Service-Token`). FastAPI publishes its own OpenAPI file (CT-16).

### DEC-11 · Redis persistence

| | |
| --- | --- |
| Source | AIBD-029 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-11 · Sprint 3 |
| Affects | P3-I2 · P6-R6 |
| Decision | ______ |

<div dir="rtl">

**القصة.** السيرفر عمل restart، والـ Redis كان فيه 5 jobs لسه ماتنفذتش. من غير persistence الـ jobs دي هتضيع، والطلبات هتفضل "مستنية" على الشاشة ومحدش هيحسبها.

</div>

**Topic.** If Redis goes down, queued jobs may be lost. Persistence is not documented.

**Options:**

1. AOF enabled (`appendfsync everysec`).
2. RDB snapshots only.
3. No persistence; rely on the sweeper that re-queues QUEUED runs.

**Recommendation.** Option 1, with the sweeper (P3-I2) as a safety net.

### DEC-12 · AI `port_setting` keys

| | |
| --- | --- |
| Source | AIBD-021 · PS-02 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-12 · Sprint 1 |
| Affects | AI-012 · P2-F9 |
| Decision | ______ |

<div dir="rtl">

**القصة.** لو وقت الـ solver أو عدد مرات إعادة المحاولة مكتوبين جوه الكود، أي تغيير محتاج developer وdeploy جديد. محتاجين قايمة متفق عليها بالإعدادات اللي الـ Backend يحطها في الـ database والـ AI يقراها.

</div>

**Topic.** AI settings must change without code changes.

**Options:**

1. Proposed list: `weather_pull_hours`, `tide_horizon_days`, `part1_stored_data_max_age_hours` (48), `part1_assessment_horizon_hours`, `part1_time_step_minutes`, `part1_min_window_minutes`, `demand_slot_minutes`, `solver_time_limit_seconds` (10), `solver_options_per_request`, `part1_max_retries` (3), `run_stale_after_seconds`, `part3_evaluation_cron`, `drift_psi_threshold`, `drift_mae_threshold`.
2. Environment variables (cannot change at runtime).

**Recommendation.** Option 1. Undocumented values are set in DEC-24 and DEC-30.

### DEC-13 · Who keeps the OpenAPI file current

| | |
| --- | --- |
| Source | Backend open inputs |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-13 · Sprint 1 |
| Affects | P1-A4 · CT-02 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Backend غيّر اسم حقل في الـ API ونسي يحدّث الـ OpenAPI. الـ Frontend بنى الشاشة على الاسم القديم، والشاشة وقعت في الـ demo. لازم يبقى فيه صاحب واحد للملف ده وقاعدة إنه يتحدث مع كل تغيير.

</div>

**Topic.** Frontend and Mobile build against the OpenAPI file, so it must stay up to date.

**Options:**

1. The Backend Team is the single owner; any PR that changes an endpoint updates the file in the same PR.
2. Each team updates its own part.

**Recommendation.** Option 1, with an OpenAPI diff in the API readiness pack (CT-23).


## AI contract v1 (C-01 to C-06)

### DEC-14 · C-01 · Part 1 run

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-001 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-14 · Sprint 1 |
| Affects | P3-I7 · P4-J3 · AI-048 · CT-09 |
| Decision | ______ |

<div dir="rtl">

**القصة.** بعد موافقة الجمارك، الـ Backend بيبعت للـ AI رسالة "احسب نوافذ الدخول للطلب ده". لو الحقول وأسباب الإعادة مش متفق عليها، الـ AI ممكن يرفض الرسالة أو يحسب غلط. ومفيش حد محدد للـ run ياخد قد إيه قبل ما نعتبره فشل.

</div>

**Topic.** The message that starts the entry-window computation for one request on `queue:part1`.

**Options:**

1. Payload: `berthing_request_id`, `reason` (CUSTOMS_APPROVAL / RECOMPUTE / MANUAL_DATA / REOPEN), `manual_forecast_run_id` when MANUAL_DATA.

**Recommendation.** Approve the proposed payload. The timeout is not documented: proposed `part1_run_timeout_seconds = 120` in `port_setting`.

### DEC-15 · C-02 · Part 2 solve

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-002 to 005 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-15 · Sprint 1 |
| Affects | P4-J3 · P4-K3 · P4-K5 · P5-O7 · AI-058 · CT-10 |
| Decision | ______ |

<div dir="rtl">

**القصة.** نفس الـ worker بيتطلب منه 4 حاجات مختلفة: توصية جديدة، إعادة توليد، رصيف اتعطل، أو سفينة اتأخرت. كل حالة ليها بيانات مختلفة، ولو الرسالة مش واضحة الـ AI مش هيعرف هو بيحل مشكلة إيه بالظبط.

</div>

**Topic.** The message for solve, regenerate, resource change and delay re-plan on `queue:part2`.

**Options:**

1. Payload: `trigger_type` (NEW_REQUEST / MANUAL / RESOURCE_CHANGE / REPLAN), `berthing_request_ids`, `purpose` (INITIAL / DELAY_REPLAN), `changed_resource`, `operational_plan_id`, `context_note`; plus the `result_detail` shape with the outcome and binding constraints.

**Recommendation.** Approve as proposed. `context_note` is stored in logs only.

### DEC-16 · C-03 · Yard placement

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-006 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-16 · Sprint 1 |
| Affects | P6-P1 · AI-066 · CT-11 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الخطة اتأكدت لسفينة حاويات، والـ Backend لازم يطلب من الـ AI توصية أماكن الحاويات في الساحة. محتاجين نتفق على شكل الطلب، ونتفق كمان إن الـ AI بيقترح بس ومش بيحجز أماكن بنفسه.

</div>

**Topic.** The yard recommendation message on `queue:part2`.

**Options:**

1. Payload: `terminal_recommendation_id` (in YARD_REC_REQUESTED) and `operational_plan_id`. The worker never reserves a slot.

**Recommendation.** Approve as proposed.

### DEC-17 · C-04 · BAPLIE parse

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-007 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-17 · Sprint 1 |
| Affects | P3-H3 · AI-030 · AI-033 · CT-12 |
| Decision | ______ |

<div dir="rtl">

**القصة.** المطلوب إن تحليل الملف ياخد 3 أو 10 أو 25 ثانية حسب "حجمه"، بس محدش عرّف يعني إيه ملف صغير أو كبير. فمش هنعرف نختبر الأداء ولا نقول إنه ناجح.

</div>

**Topic.** The BAPLIE parsing message on `queue:edi`.

**Options:**

1. Payload: `baplie_file_id` only; the worker reads the rest from the row. The NFR-PERF-2 size classes (3 / 10 / 25 seconds) need size definitions.

**Recommendation.** Approve. Size classes (proposed): small up to 500 containers, medium up to 5,000, large up to 20,000.

### DEC-18 · C-05 · Validation

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-008 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-18 · Sprint 1 |
| Affects | AI-F03 · P4-K4 · P6-P3 · CT-13 |
| Decision | ______ |

<div dir="rtl">

**القصة.** لما الموظف يعدّل الرصيف، الـ Backend هيسأل الـ AI "التعديل ده سليم؟". لو شكل السؤال والإجابة مش متفق عليهم، رسالة الخطأ اللي هتوصل للموظف مش هتقول هو كسر أنهي قيد.

</div>

**Topic.** The shape of the validation request and its result. Depends on DEC-03 and DEC-10.

**Options:**

1. If DEC-03 = FastAPI: `POST /internal/v1/validate` with `validation_type` (OVERRIDE / YARD_ADJUSTMENT), `subject_id`, `proposed_change`; the answer `{valid, violations[]}` comes back immediately.
2. If async: the same fields plus `request_token`, with the result returned through C-06.

**Recommendation.** Option 1 for override and yard adjustment; BAPLIE correction async on `queue:edi` with the same fields.

### DEC-19 · C-06 · Completion message

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-010 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-19 · Sprint 1 |
| Affects | P3-I3 · AI-011 · CT-14 |
| Decision | ______ |

<div dir="rtl">

**القصة.** لما الـ AI يخلص، رسالة "خلصت" لازم تقول خلص إيه، ونجح ولا فشل، وليه. من غير كده الـ Backend مش هيعرف يغيّر حالة الطلب صح ولا يبعت الإشعار المناسب.

</div>

**Topic.** The shape of the completion message the worker sends to the Backend.

**Options:**

1. `{contract_version, job_type, run_id, status, outcome, error_category, finished_at}`; Part 3 uses it for DRIFT_ALERT.

**Recommendation.** Approve; the list name is `queue:ai-results`.


## AI decisions (inputs and logic)

### DEC-20 · Tug-count formula

| | |
| --- | --- |
| Source | OD-04 · RSK-01 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-20 · Sprint 2 |
| Affects | AI-054 · AI-055 |
| Decision | ______ |

<div dir="rtl">

**القصة.** سفينة طولها 300 متر داخلة الميناء. محتاجة كام قاطرة؟ 2 ولا 3 ولا 4؟ القاعدة دي بيقررها خبراء القطر مش المبرمجين، ولحد دلوقتي محدش ادّاها لنا. من غيرها الـ solver مش هيعرف يحجز قاطرات.

</div>

**Topic.** The number of tugs per vessel (from GT, DWT and tug power) is not defined, and this blocks CP-SAT.

**Options:**

1. Input from the Tug Manager / Marine Safety Officer.
2. A provisional table by vessel length until the input arrives.

**Recommendation.** Request the formula formally in Sprint 1. If it does not arrive, the provisional table is marked "unvalidated" in the rationale and can be replaced without code changes (pluggable rule).

### DEC-21 · Phase 1 delay-risk rule

| | |
| --- | --- |
| Source | OD-05 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-21 · Sprint 3 |
| Affects | AI-053 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الشاشة المفروض تقول للموظف "الخطة دي احتمال تتأخر 30%". بس إحنا لسه مافيش عندنا تاريخ تأخيرات نتعلم منه. لازم نتفق على قاعدة بسيطة مؤقتة، أو نعرض "مش متقيّم".

</div>

**Topic.** B4 needs a rule to estimate delay probability before any history exists.

**Options:**

1. NULL until a rule is approved.
2. A simple rule from weather margin and port congestion.

**Recommendation.** A simple rule approved in Sprint 1 so B4 is fully delivered. If not approved, it writes NULL and P-38 shows "Not assessed".

### DEC-22 · Financial-impact data in ranking

| | |
| --- | --- |
| Source | OD-06 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-22 · Sprint 4 |
| Affects | AI-055 · AI-057 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الترتيب المطلوب للاختيارات بالوقت الأول وبعدين بالتكلفة المالية. بس مفيش أي داتا عن تكلفة انتظار السفينة أو تشغيل الرصيف، فمش هنعرف نرتب بالفلوس.

</div>

**Topic.** The documented order is time first, then financial impact, but there is no cost data.

**Options:**

1. Time-only ranking until a cost model is approved.
2. An estimated cost per waiting hour.

**Recommendation.** Option 1.

### DEC-23 · Objective terms, weights and number of options

| | |
| --- | --- |
| Source | OD-07 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-23 · Sprint 1 |
| Affects | AI-009 · AI-055 · AI-057 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ solver محتاج يعرف "أحسن خطة" يعني إيه: أقل انتظار للسفن؟ ولا أعلى استغلال للأرصفة؟ ولا الاتنين؟ وبأي نسبة؟ وكمان يطلع للموظف كام اختيار؟

</div>

**Topic.** CP-SAT needs a clear objective.

**Options:**

1. Codes for waiting time and resource utilisation, and 3 options per request.
2. Lexicographic: time, then utilisation.

**Recommendation.** Option 1 with initial weights in the seed data (AI-009), adjustable later.

### DEC-24 · Part 1 settings: horizon, time step, minimum window, slot

| | |
| --- | --- |
| Source | OD-09 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-24 · Sprint 4 |
| Affects | AI-047 · AI-048 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ AI بيدوّر على نوافذ دخول آمنة. بيدوّر لقدّام قد إيه؟ بيفحص كل كام دقيقة؟ وأقل نافذة مقبولة طولها قد إيه؟ من غير الأرقام دي الحساب مش هيبدأ.

</div>

**Topic.** The window computation needs fixed values set by the Marine Safety Officer and staff.

**Options:**

1. Horizon 72 hours, step 30 minutes, minimum window 60 minutes, demand slot 60 minutes (proposed).

**Recommendation.** Approve the proposed values as `port_setting` keys, changeable later without code.

### DEC-25 · Uncertainty margin and window confidence

| | |
| --- | --- |
| Source | OD-11 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-25 · Sprint 3 |
| Affects | AI-044 · AI-048 |
| Decision | ______ |

<div dir="rtl">

**القصة.** التوقعات الجوية مش مضمونة 100%. المفروض نسيب هامش أمان، ونعرض للموظف "واثقين من النافذة دي بنسبة كذا". بس حساب الهامش ده اتأجل لـ future work، فلازم نقرر نعرض إيه دلوقتي.

</div>

**Topic.** A6 (margin) is future work, so MVP behaviour must be defined.

**Options:**

1. Zero margin and confidence = NULL.

**Recommendation.** This option. P-37 shows no confidence value.

### DEC-26 · Weather and marine providers

| | |
| --- | --- |
| Source | OD-12 · RSK-04 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-26 · Sprint 4 |
| Affects | AI-020 · AI-040 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Part 1 محتاج توقعات رياح وأمواج ورؤية لميناء دمياط. لسه ماختارناش هنجيبها منين، ولا اتأكدنا إن الرخصة تسمح نستخدمها، ولا لو المصدر الأساسي وقع هنعمل إيه.

</div>

**Topic.** A primary and a fallback are needed covering every A4 variable (wind, visibility, waves, current, sea level).

**Options:**

1. Open-Meteo (Forecast + Marine) as primary, and a second provider as fallback after comparing licence and coverage.

**Recommendation.** Compare 2 or 3 providers on variables, licence and coverage for Damietta, and pick two in Sprint 1.

### DEC-27 · Tidal constants source, datum and reference

| | |
| --- | --- |
| Source | OD-13 · RSK-05 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-27 · Sprint 4 |
| Affects | AI-021 · AI-042 · P2-F5 |
| Decision | ______ |

<div dir="rtl">

**القصة.** عشان نحسب المد لازم ثوابت فلكية خاصة بالميناء. ولازم عمق الأرصفة والمد يتقاسوا من نفس المستوى المرجعي. لو المستويين مختلفين بمتر، ممكن نقول إن السفينة تعدّي وهي فعلًا هتلمس القاع.

</div>

**Topic.** A2 needs published constants for the reference port and a single datum shared with the depths.

**Options:**

1. Published constants for Damietta on LAT.

**Recommendation.** This option, with a published tide table as the validation reference and an error tolerance set in DEC-30.

### DEC-28 · Definition of moves

| | |
| --- | --- |
| Source | OD-14 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-28 · Sprint 3 |
| Affects | AI-052 |
| Decision | ______ |

<div dir="rtl">

**القصة.** زمن خدمة السفينة بيتحسب من عدد حركات الونش. ملف الـ BAPLIE فيه الحاويات اللي هتنزل بس، ومش فيه اللي هتطلع. لازم نتفق هنعرف العدد الكلي إزاي.

</div>

**Topic.** Service time (B3) needs the number of moves.

**Options:**

1. Discharge from the BAPLIE + loading count entered or estimated.

**Recommendation.** This option. Loading count is an optional request field; if empty it is estimated equal to discharge.

### DEC-29 · Yard recommendation method, objective and confidence

| | |
| --- | --- |
| Source | OD-15 · RSK-09 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-29 · Sprint 3 |
| Affects | AI-065 · AI-066 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ AI المفروض يقترح الحاويات تتحط فين في الساحة، بس محدش حدد يعمل ده إزاي. هل بقواعد بسيطة زي "المبرّد جنب الكهربا"؟ ولا بموديل optimization؟ وإيه اللي يخلّينا "واثقين" في الاقتراح؟

</div>

**Topic.** The B8 method is not defined.

**Options:**

1. Option A: rule-based heuristic (group by movement, type and weight, then compatible blocks).
2. Option B: CP-SAT assignment (needs an objective that is not documented).

**Recommendation.** Option A; confidence = share of containers placed in a zone of their preferred type.

### DEC-30 · Numeric thresholds register

| | |
| --- | --- |
| Source | OD-16 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-30 · Sprint 2 |
| Affects | AI-008 · AI-072 |
| Decision | ______ |

<div dir="rtl">

**القصة.** أرقام كتير الشغل محتاجها ومحدش حددها. إمتى نقول إن الموديل بدأ يبوظ (drift)؟ وكام سم خطأ مسموح في حساب المد؟ من غيرها مش هنعرف نقول إن أي حاجة نجحت أو فشلت.

</div>

**Topic.** Drift, deviation significance, data sufficiency, tide tolerance, BAPLIE size classes, coverage.

**Options:**

1. One register owned by the AI Team and approved by the whole team.

**Recommendation.** This option: inputs prepared (QA-AI1), approved in Sprint 1, final write-up in AI-008.

### DEC-31 · Part 3 scheduling host

| | |
| --- | --- |
| Source | OD-17 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-31 · Sprint 6 |
| Affects | AI-073 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Part 3 بيقيّم أداء الـ AI بشكل دوري، بس مفيش حد مسؤول يشغّله، ومفيش queue خاصة بيه. لازم نحدد مين اللي بيقول له "يلا اشتغل".

</div>

**Topic.** There is no `queue:part3`.

**Options:**

1. A scheduler inside the Part 3 worker.
2. The Laravel scheduler enqueues (needs a new queue).

**Recommendation.** Option 1.

### DEC-32 · Availability semantics for pilots and tug masters

| | |
| --- | --- |
| Source | OD-19 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-32 · Sprint 3 |
| Affects | AI-050 · P5-M1 |
| Decision | ______ |

<div dir="rtl">

**القصة.** المرشد ده "متاح"؟ هو في ورديته، بس اتقترح لسفينة تانية في نفس الوقت ولسه محدش أكد. لو الـ AI والـ Backend عرّفوا "متاح" بشكلين مختلفين، هنحجز نفس المرشد لسفينتين.

</div>

**Topic.** B2 and B5 need a definition of "available".

**Options:**

1. A pilot is on shift and not proposed or assigned in an overlapping window. A tug is available when its status is available and its master is on shift.

**Recommendation.** This option.

### DEC-33 · Manual-planning baseline

| | |
| --- | --- |
| Source | OD-20 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-33 · Sprint 7 |
| Affects | AI-084 |
| Decision | ______ |

<div dir="rtl">

**القصة.** عشان نقول إن الـ AI أحسن من التخطيط اليدوي، لازم نعرف التخطيط اليدوي بيتعمل إزاي بالظبط ونقيسه على نفس السيناريوهات. من غير كده المقارنة مالهاش معنى.

</div>

**Topic.** Evaluating the AI needs a comparison with manual planning.

**Options:**

1. Replay scenarios with documented manual rules agreed with an expert.

**Recommendation.** This option; the QA Team prepares the procedure (QA-AI1).

### DEC-34 · Building A4 rules on synthetic data

| | |
| --- | --- |
| Source | Plan decision |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-34 · Sprint 3 |
| Affects | AI-044 · AI-051 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Part 2 (أهم جزء) محتاج قواعد الأمان بتاعة الـ Part 1 عشان يبدأ. لو استنينا الـ Part 1 يخلص كله بالداتا الحقيقية، الـ Part 2 هيتأخر كذا sprint. الحل إننا نبني القواعد على داتا تجريبية الأول.

</div>

**Topic.** The documented critical path is AI-040 → 041 → 043 → 044, but Part 2 needs AI-044 early.

**Options:**

1. A4 is built and tested on synthetic series; the real surge feed joins later.
2. Wait for the full Part 1 chain.

**Recommendation.** Option 1, so Part 2 starts CP-SAT in Sprint 4.


## Product and screen decisions

### DEC-35 · Sign-in identifier

| | |
| --- | --- |
| Source | Screens P-16/P-52 · FR-AC-01 · FR-AC-09 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-35 · Sprint 1 |
| Affects | P1-C1 · P1-C3 · FE-025 · MB-P52 |
| Decision | ______ |

<div dir="rtl">

**القصة.** شاشة الدخول على الويب بتطلب email، بس الـ requirements بتقول إن المستخدم بيتعمل بـ username وتليفون ومن غير email خالص. يعني المستخدم مش هيلاقي حاجة يدخل بيها.

</div>

**Topic.** Screens: email on the web, username on the tablet. The FRD creates users with name, username and phone, with no email.

**Options:**

1. Username on web and tablet.
2. Add an email to users and use it on the web.

**Recommendation.** Option 1 because it matches the requirements. P-16 uses username instead of email.

### DEC-36 · One role per user vs role history

| | |
| --- | --- |
| Source | Screens P-24 · P2-E2 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-36 · Sprint 2 |
| Affects | P2-E2 · FE-045 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الشاشة بتقول إن كل مستخدم ليه دور واحد، والـ Backend معمول إنه يدّي أدوار وينهيها بتاريخ. لو موظف اتنقل من Tug Officer لـ Pilotage Officer، هل بيبقى معاه الاتنين؟ ولا القديم بينتهي؟

</div>

**Topic.** The screens say one role; the Backend assigns and ends roles with dates.

**Options:**

1. One active role at a time; history kept with `active_to`.

**Recommendation.** This option.

### DEC-37 · "Reject with reason" on P-44 and P-47

| | |
| --- | --- |
| Source | Screens P-44/P-47 · P5-M2 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-37 · Sprint 6 |
| Affects | P5-M2 · FE-067 · FE-070 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الشاشة فيها زرار "رفض بسبب" للمرشد المقترح، بس الـ Backend مفيهوش endpoint للرفض، وفيه تأكيد أو استبدال بس. لو الـ Frontend عمل الزرار، مش هيلاقي حاجة يكلمها.

</div>

**Topic.** The Backend tasks only have confirm or replace.

**Options:**

1. Add reject with a reason (new endpoint and component status).
2. Confirm or replace only.

**Recommendation.** Option 2: replace covers the case and no new status is needed.

### DEC-38 · Where to activate the tide constituent set

| | |
| --- | --- |
| Source | Screens P-59 · P2-F5 |
| Owner | UI/UX Team |
| Status | Open |
| Closing task | DEC-38 · Sprint 3 |
| Affects | P2-F5 · FE-076 |
| Decision | ______ |

<div dir="rtl">

**القصة.** تفعيل ثوابت المد مع فحص المستوى المرجعي محتاج زرار في شاشة. ممكن يبقى عند الـ Marine Safety Officer أو عند الـ Port Admin، ومحدش قرر مين.

</div>

**Topic.** Activation with the datum check can live on P-59 or P-26.

**Options:**

1. P-59 (Marine Safety Officer).
2. P-26 (Port Admin, next to the chart datum).

**Recommendation.** Option 1, since it is the same Backend task (P2-F5) and the same decision owner.

### DEC-39 · CT Supervisor status list

| | |
| --- | --- |
| Source | Screens P-55 · Flutter tasks |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-39 · Sprint 6 |
| Affects | P5-O8 · MB-P55 |
| Decision | ______ |

<div dir="rtl">

**القصة.** مشرف التيرمنال بيسجل حالة الشغل من التابلت، بس محدش حدد الحالات اللي هيختار منها. هل هي نفس حالات المرشد (بدأ وخلص)؟ ولا حالات خاصة بالتيرمنال؟

</div>

**Topic.** P-55 says the terminal status list needs confirmation.

**Options:**

1. The same task statuses: In progress and Executed.
2. Terminal-specific statuses from `status_type`.

**Recommendation.** Option 1 for the MVP: In progress and Executed on the terminal component.

### DEC-40 · Mobile Acknowledge event type and payload

| | |
| --- | --- |
| Source | Flutter R1 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-40 · Sprint 6 |
| Affects | P5-O3 · MB-P55 · MB-P19 · CT-07 |
| Decision | ______ |

<div dir="rtl">

**القصة.** المرشد بيدوس "استلمت" على الإشعار وهو مش متصل بالنت، فالحدث بيتحفظ على الجهاز ويتبعت بعدين. لو شكل الحدث مش متفق عليه، الـ Backend هيرفضه، والنظام هيفضل يصعّد كأن المرشد ماستلمش.

</div>

**Topic.** Acknowledge goes through the Outbox and needs an agreed event type.

**Options:**

1. `event_type = "ACKNOWLEDGE"` and `payload = {notification_id}`.

**Recommendation.** This option, documented in CT-07.

### DEC-41 · Automatic sync right after saving an event while online

| | |
| --- | --- |
| Source | Flutter F4 (suggested) |
| Owner | Mobile Team |
| Status | Open |
| Closing task | DEC-41 · Sprint 4 |
| Affects | MB-F4A |
| Decision | ______ |

<div dir="rtl">

**القصة.** المرشد داس "بدأت" والنت شغال. هل التحديث يتبعت على طول؟ ولا يستنى لحد ما يدوس زرار sync؟ لو استنى، المكتب هيشوف الحالة متأخرة.

</div>

**Topic.** Should the app sync immediately after saving an event when it is online?

**Options:**

1. Yes, immediate sync.
2. Only on triggers (connection restored, sync button).

**Recommendation.** Option 1 so updates reach the office quickly.

### DEC-42 · Staff pages on the tablet and a provisioning screen

| | |
| --- | --- |
| Source | Screens OQ-9 · A-2 |
| Owner | Leads Council |
| Status | Open |
| Closing task | DEC-42 · Sprint 2 |
| Affects | — |
| Decision | ______ |

<div dir="rtl">

**القصة.** ملف الشاشات القديم كان فيه سؤال: هل موظفي المكتب يستخدموا التابلت؟ وهل فيه شاشة لتجهيز الأجهزة؟ الحاجتين دول مش موجودين في الـ requirements، ولازم نقفل السؤال عشان محدش يشتغل عليهم.

</div>

**Topic.** They are not in the requirements.

**Options:**

1. Not in the MVP.
2. Add them.

**Recommendation.** Option 1.

### DEC-43 · Recommendation confidence field on P-38

| | |
| --- | --- |
| Source | FE-OQ-11 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-43 · Sprint 6 |
| Affects | FE-059 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Frontend عايز يعرض "درجة الثقة" في التوصية، بس مفيش حقل زي ده في الـ database، والـ AI مش بيحسبه. يا نشيله من الشاشة، يا نضيفه في كل الطبقات.

</div>

**Topic.** There is no stored confidence field for a recommendation.

**Options:**

1. Not shown.
2. Add a field.

**Recommendation.** Option 1: P-38 shows the objective score and rationale only.

### DEC-44 · Storing the clock-skew review note

| | |
| --- | --- |
| Source | FE-OQ-31 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-44 · Sprint 6 |
| Affects | P5-O5 · FE-065 |
| Decision | ______ |

<div dir="rtl">

**القصة.** ساعة التابلت كانت غلط، فالحدث وصل بوقت مش منطقي واتعلّم "مشكوك فيه". الموظف عايز يكتب ملاحظة إنه راجعه، بس مفيش مكان يتحفظ فيه الكلام ده.

</div>

**Topic.** P-41 shows a Clock-skew suspect flag; where a review note is stored is unclear.

**Options:**

1. Show the flag only, no note.
2. A note field on `actual_status_update`.

**Recommendation.** Option 1 for the MVP.

### DEC-45 · Display time zone

| | |
| --- | --- |
| Source | FE-OQ-14 |
| Owner | Frontend Team |
| Status | Open |
| Closing task | DEC-45 · Sprint 1 |
| Affects | FE-006 · MB-F1 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ database بتسجل كل حاجة بتوقيت UTC. لو الشاشة عرضت الوقت زي ما هو، الموظف هيشوف السفينة جاية الساعة 7 وهي فعلًا جاية الساعة 10 بتوقيت مصر.

</div>

**Topic.** The database is UTC and shifts are local time.

**Options:**

1. Display in port time from `port_profile.timezone`.
2. User device time.

**Recommendation.** Option 1 on web and mobile.

### DEC-46 · Supported browsers and viewports

| | |
| --- | --- |
| Source | FE-OQ-23 |
| Owner | Frontend Team |
| Status | Open |
| Closing task | DEC-46 · Sprint 1 |
| Affects | FE-006 · FE-108 |
| Decision | ______ |

<div dir="rtl">

**القصة.** من غير ما نحدد المتصفحات والمقاسات اللي هندعمها، الـ QA مش هيعرف يختبر على إيه، وأي مشكلة على متصفح قديم هتبقى bug ملهاش نهاية.

</div>

**Topic.** The test scope must be defined.

**Options:**

1. Latest two versions of Chrome, Edge and Firefox; desktop from 1280 px and tablet from 768 px.

**Recommendation.** This option.

### DEC-47 · Backend environment for development and testing

| | |
| --- | --- |
| Source | FE-OQ-29 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-47 · Sprint 2 |
| Affects | FE-101 · MB-F4B · QA-01 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Frontend والـ Mobile عايزين يجربوا على API حقيقي، بس الـ Backend شغال على جهازه بس. من غير سيرفر مشترك بيتحدث أول بأول، كل تيم هيختبر على حاجة مختلفة.

</div>

**Topic.** Frontend, Mobile and QA need a server with the latest develop and seed data.

**Options:**

1. A dev server updated on every merge to develop, and a separate demo updated on every release.

**Recommendation.** This option.

### DEC-48 · Field roles on the web

| | |
| --- | --- |
| Source | FE-OQ-12 |
| Owner | Leads Council |
| Status | Open |
| Closing task | DEC-48 · Sprint 2 |
| Affects | FE-021 |
| Decision | ______ |

<div dir="rtl">

**القصة.** المرشد فتح الموقع من الكمبيوتر وعمل login. مفيش ليه أي شاشة على الويب، فهيشوف إيه؟

</div>

**Topic.** What happens when a pilot, tug master or CT Supervisor signs in on the web.

**Options:**

1. P-20 with a "use the mobile app" message.
2. A web version of My Tasks.

**Recommendation.** Option 1.


## Closed items (for reference)

### DEC-49 · Status and error colours and the icon set

| | |
| --- | --- |
| Source | FE-OQ-21 · FE-OQ-22 |
| Owner | UI/UX Team |
| Status | Closed |
| Closing task | — |
| Affects | FE-015 · FE-018 |
| Decision | Closed. |

<div dir="rtl">

**القصة.** الـ Frontend كان مستني يعرف ألوان الأخطاء والتحذيرات وشكل الأيقونات. الحاجات دي اتعتمدت مع الهوية.

</div>

**Topic.** Colours and button styles are approved.

### DEC-50 · BAPLIE correction and withdraw

| | |
| --- | --- |
| Source | Old screens file vs FRD |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | P3-H5 · P3-H6 · FE-052 |
| Decision | Closed: implemented (P3-H5, P3-H6) and shown on P-31. |

<div dir="rtl">

**القصة.** ملف الشاشات القديم كان بيقول "مفيش تعديل ولا سحب لملف الـ BAPLIE"، والـ requirements بتقول فيه. اتقفلت على حسب الـ requirements.

</div>

**Topic.** The requirements include correction and withdraw.

### DEC-51 · Shared berths

| | |
| --- | --- |
| Source | Old screens file vs P2-F2 |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | P2-F2 · FE-049 |
| Decision | Closed: allowed; P-28 takes one or more terminals. |

<div dir="rtl">

**القصة.** ملف الشاشات القديم كان بيقول "كل رصيف لتيرمنال واحد"، والـ database بتسمح برصيف مشترك. اتقفلت إن الرصيف المشترك مسموح.

</div>

**Topic.** The requirements and the schema allow a shared berth.

### DEC-52 · Boat management (P-61)

| | |
| --- | --- |
| Source | Old screens file |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | — |
| Decision | Closed: future work. |

<div dir="rtl">

**القصة.** كانت فيه شاشة لإدارة الـ boats، بس مفيش جدول ولا requirement ليها. اتنقلت لـ future work.

</div>

**Topic.** There is no boat entity in the requirements or the schema.

### DEC-53 · Screens baseline

| | |
| --- | --- |
| Source | Old Figma |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | UX-W1 to UX-W6 |
| Decision | Closed. |

<div dir="rtl">

**القصة.** تصميمات الـ Figma القديمة كانت مبنية على ملف شاشات قديم. ملف الشاشات الجديد اتعتمد وبقى هو المرجع.

</div>

**Topic.** The new screens file is approved.

### DEC-54 · Licence, SaaS and READ_ONLY in the task files

| | |
| --- | --- |
| Source | D-11 · OD-18 · AIBD-023 |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | — |
| Decision | Closed: future work. |

<div dir="rtl">

**القصة.** ملفات التاسكات كان فيها شغل للرخص والـ READ_ONLY، وده كله اتأجل لـ future work.

</div>

**Topic.** Licence and SaaS are approved as future work, and READ_ONLY behaviour is defined by the team.

### DEC-55 · TIMING and NCT recommendation producers

| | |
| --- | --- |
| Source | OD-23 |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | — |
| Decision | Closed: future work. |

<div dir="rtl">

**القصة.** كان فيه سؤال مين هيعمل توصيات التوقيت والتيرمنال غير الحاويات. الاتنين برا الـ MVP.

</div>

**Topic.** Outside the current scope.

### DEC-56 · SaaS API location and licence signing key

| | |
| --- | --- |
| Source | Backend open inputs |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | — |
| Decision | Closed: future work. |

<div dir="rtl">

**القصة.** الـ Backend كان سايب سؤالين: الـ SaaS API هيتحط فين، ومفتاح توقيع الرخصة. الاتنين تبع الـ SaaS اللي اتأجل.

</div>

**Topic.** Both belong to SaaS and licensing.
