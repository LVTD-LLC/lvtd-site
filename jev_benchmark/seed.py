"""OpenRouter catalogue checked 2026-09-27; explicit IDs, not auto routes."""

MODELS = [
    ("openai/gpt-6-astra", "GPT-6 Astra", "OpenAI"),
    ("anthropic/claude-fable-5.1", "Claude Fable 5.1", "Anthropic"),
    ("google/gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview", "Google"),
    ("deepseek/deepseek-v4-pro-0813", "DeepSeek V4 Pro", "DeepSeek"),
    ("xiaomi/mimo-v2.6-pro", "MiMo V2.6 Pro", "Xiaomi"),
    ("qwen/qwen3.8-max-prime", "Qwen3.8 Max Prime", "Alibaba / Qwen"),
    ("moonshotai/kimi-k3", "Kimi K3", "Moonshot AI"),
    ("z-ai/glm-5.3-prime", "GLM 5.3 Prime", "Z.ai"),
    ("mistralai/mistral-medium-3-5", "Mistral Medium 3.5", "Mistral"),
    ("x-ai/grok-4.7", "Grok 4.7", "xAI"),
]

QUESTIONS = [
    {
        "slug": "writing-the-case-for-a-modular-monolith",
        "title": "The case for a modular monolith",
        "category": "writing",
        "prompt": (
            "Write an 800-1,000 word blog post for a technical founder "
            "deciding whether to split a Django SaaS into microservices. The "
            "team has four engineers, 20,000 monthly active users, a "
            "PostgreSQL database, a 99.9% availability target, occasional "
            "five-second reporting queries, and a six-week runway to launch a "
            "paid enterprise plan. These are hypothetical facts, not evidence "
            "of any real company. Make a concrete recommendation, fairly "
            "present the strongest opposing argument, and give a staged six- "
            "week plan. Address data ownership, background jobs, deployment "
            "rollback, observability, security boundaries, and how to measure "
            "whether the plan worked. Include one small quantitative "
            "calculation with assumptions and one realistic failure scenario. "
            "Distinguish supplied facts from assumptions; do not invent "
            "sources, quotations, or customer results. Use a compelling title, "
            "clear sections, and specific prose rather than generic AI hype. "
            "The post must stand alone without web browsing."
        ),
        "rubric": (
            "Prioritize technically sound advice grounded in the supplied "
            "constraints, coherent tradeoffs and sequencing, accurate "
            "arithmetic, and actionable success criteria. Then judge clarity, "
            "structure, audience fit, originality, and adherence to the "
            "requested length. Penalize fabricated evidence and generic "
            "filler."
        ),
    },
    {
        "slug": "coding-offline-dynamic-connectivity",
        "title": "Offline dynamic connectivity with rollback",
        "category": "coding",
        "prompt": (
            "Implement solve(n, operations) in Python 3.12 for an initially "
            "empty undirected graph on vertices 0 through n-1. Operations are "
            'tuples ("add", u, v), ("remove", u, v), or ("connected", u, v). '
            "Return a list of booleans for the connected operations in input "
            "order. There can be 200,000 vertices and 200,000 operations. "
            "Edges are unordered and have reference counts: adding an already- "
            "present edge increments its count, removing decrements it, and "
            "the edge disappears only when the count reaches zero. Removing a "
            "zero-count edge is a no-op. Self-loops are allowed. All vertex "
            "IDs are valid. The input must not be mutated. Provide complete "
            "executable code using only the standard library, explain its "
            "invariants and correctness, and give time and memory bounds. Use "
            "offline edge-active intervals, a segment tree over time, and a "
            "rollback disjoint-set union without path compression. Address "
            "edges active until the end, reversed endpoints, repeated "
            "additions/removals, and empty input. Include deterministic tests "
            "for those cases and a randomized differential test against a "
            "simple BFS oracle on small graphs. Keep the explanation and code "
            "within 2,500 words; do not execute tools or access the internet."
        ),
        "rubric": (
            "Correct reference-counted edge intervals, canonical endpoints, "
            "rollback invariants without path compression, exact query "
            "ordering and interval boundaries are essential. Evaluate "
            "executable completeness, asymptotic scalability, Python memory "
            "practicality, proofs, and tests including the BFS oracle. "
            "Confidently wrong algorithms are worse than concise correct ones."
        ),
    },
    {
        "slug": "math-stopping-time-and-variance",
        "title": "A stopping-time expectation and variance",
        "category": "math",
        "prompt": (
            "Let X_1, X_2, ... be independent Uniform(0,1) random variables, "
            "S_n = X_1 + ... + X_n, and N = min{n >= 1 : S_n > 2}. Derive "
            "exact closed forms for E[N] and Var(N), without simulation or "
            "numerical integration. First derive P(S_n <= 2) from a simplex- "
            "volume argument using inclusion-exclusion, carefully treating "
            "n=0, n=1 and boundary cases. Then justify the tail-sum identities "
            "for the first and second moments and evaluate the resulting "
            "infinite sums. Show the algebra, establish convergence, and give "
            "numerical sanity checks of the final constants. Finally "
            "generalize the expression for E[N_t] to an arbitrary real "
            "threshold t > 0, where N_t = min{n >= 1 : S_n > t}; a finite sum "
            "involving floor(t) and exponentials is acceptable. Keep the "
            "solution self-contained within 2,000 words and explicitly explain "
            "why strict versus non-strict threshold events do or do not "
            "matter."
        ),
        "rubric": (
            "Prioritize a valid inclusion-exclusion derivation, correct low-n "
            "and boundary cases, justified moment identities and convergence, "
            "exact expectation and variance algebra, and a correct arbitrary- "
            "threshold generalization. Check numerical sanity and distinguish "
            "continuity for positive n from the deterministic n=0 case. "
            "Presentation alone cannot compensate for mathematical mistakes."
        ),
    },
]
