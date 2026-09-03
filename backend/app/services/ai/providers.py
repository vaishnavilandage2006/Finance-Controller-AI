def _cause_category(reason):
    """Bucket a per-record exception reason into a summary category."""
    if not reason:
        return "Other reconciliation issue"
    r = reason.lower()
    if "duplicate" in r:
        return "Duplicate"
    if "no settlement" in r or "settlement evidence is missing" in r or "missing settlement" in r:
        return "Missing settlement"
    if "no counterpart record" in r or "missing reference" in r or "reference not found" in r:
        return "Missing reference"
    if "differ" in r or "mismatch" in r or "variance" in r or "does not match" in r:
        return "Settlement amount mismatch"
    return "Other reconciliation issue"


class AIProvider:
    def answer(self, question, context):
        raise NotImplementedError


class MockAIProvider(AIProvider):

    def answer(self, question, context):
        q = question.lower().strip()
        k = context

        # -------------------------------------------------
        # TRANSACTION-AWARE CONTEXT
        # -------------------------------------------------

        reconciliation_records = k.get(
            "reconciliation_records",
            []
        )

        risk_records = k.get(
            "risk_records",
            []
        )

        review_records = k.get(
            "review_records",
            []
        )

        # -------------------------------------------------
        # BASIC FINANCIAL METRICS
        # -------------------------------------------------

        revenue = float(
            k.get("revenue", 0) or 0
        )

        expenses = float(
            k.get("expenses", 0) or 0
        )

        net_profit = float(
            k.get("net_profit", 0) or 0
        )

        cash_balance = float(
            k.get("cash_balance", 0) or 0
        )

        reconciliation = float(
            k.get("reconciliation_rate", 0) or 0
        )

        total_transactions = int(
            k.get("total_transactions", 0) or 0
        )

        high_risk = int(
            k.get("high_risk", 0) or 0
        )

        refunds = float(
            k.get("refunds", 0) or 0
        )

        fees = float(
            k.get("fees", 0) or 0
        )

        largest_variance = float(
            k.get("largest_variance", 0) or 0
        )

        currency = k.get(
            "currency",
            "INR"
        )

        profit_margin = (
            (net_profit / revenue) * 100
            if revenue
            else 0
        )

        # =================================================
        # SPECIFIC TRANSACTION INVESTIGATION
        # =================================================

        transaction_id = None

        for record in (
            reconciliation_records
            + risk_records
            + review_records
        ):
            tid = record.get(
                "transaction_id"
            )

            if (
                tid
                and tid.lower() in q
            ):
                transaction_id = tid
                break

        if transaction_id:

            reconciliation_item = next(
                (
                    r
                    for r in reconciliation_records
                    if r.get("transaction_id")
                    == transaction_id
                ),
                None
            )

            risk_item = next(
                (
                    r
                    for r in risk_records
                    if r.get("transaction_id")
                    == transaction_id
                ),
                None
            )

            review_item = next(
                (
                    r
                    for r in review_records
                    if r.get("transaction_id")
                    == transaction_id
                ),
                None
            )

            lines = [
                f"Transaction Investigation: "
                f"{transaction_id}",
                "",
            ]

            if reconciliation_item:

                lines.append(
                    "Reconciliation"
                )

                lines.append(
                    f"• Status: "
                    f"{reconciliation_item.get('reconciliation_status')}"
                )

                lines.append(
                    f"• Variance: "
                    f"{reconciliation_item.get('variance', 0):,.2f} "
                    f"{reconciliation_item.get('currency', currency)}"
                )

                if reconciliation_item.get(
                    "reason"
                ):
                    lines.append(
                        f"• Reason: "
                        f"{reconciliation_item.get('reason')}"
                    )

                lines.append("")

                if reconciliation_item.get(
                    "amount"
                ) is not None:

                    lines.append(
                        f"• Transaction amount: "
                        f"{reconciliation_item.get('amount'):,.2f} "
                        f"{reconciliation_item.get('currency', currency)}"
                    )

                if reconciliation_item.get(
                    "settlement_amount"
                ) is not None:

                    lines.append(
                        f"• Settlement amount: "
                        f"{reconciliation_item.get('settlement_amount'):,.2f} "
                        f"{reconciliation_item.get('currency', currency)}"
                    )

                if reconciliation_item.get(
                    "merchant"
                ):
                    lines.append(
                        f"• Merchant: "
                        f"{reconciliation_item.get('merchant')}"
                    )

                if reconciliation_item.get(
                    "vendor"
                ):
                    lines.append(
                        f"• Vendor: "
                        f"{reconciliation_item.get('vendor')}"
                    )

                if reconciliation_item.get(
                    "date"
                ):
                    lines.append(
                        f"• Date: "
                        f"{reconciliation_item.get('date')}"
                    )

            if risk_item:

                lines.extend([
                    "",
                    "Risk Assessment",
                    f"• Risk score: "
                    f"{risk_item.get('risk_score', 0):.2f}",
                    f"• Risk level: "
                    f"{risk_item.get('risk_level', 'UNKNOWN')}",
                ])

                factors = risk_item.get(
                    "risk_factors",
                    []
                )

                if factors:

                    if isinstance(
                        factors,
                        list
                    ):
                        factor_text = ", ".join(
                            str(x)
                            for x in factors
                        )
                    else:
                        factor_text = str(
                            factors
                        )

                    lines.append(
                        f"• Risk factors: "
                        f"{factor_text}"
                    )

            if review_item:

                lines.extend([
                    "",
                    "Review Queue",
                    f"• Review ID: "
                    f"{review_item.get('id', 'N/A')}",
                    f"• Review status: "
                    f"{review_item.get('status', 'UNKNOWN')}",
                ])

                if review_item.get(
                    "note"
                ):
                    lines.append(
                        f"• Reviewer note: "
                        f"{review_item.get('note')}"
                    )

            lines.extend([
                "",
                "Controller Recommendation",
                "• Verify the transaction against its "
                "settlement evidence.",
                "• Review the reconciliation variance "
                "and supporting records.",
            ])

            if risk_item:
                lines.append(
                    "• Consider the risk score and listed "
                    "risk factors before approval."
                )

            if review_item:
                lines.append(
                    "• Follow the current review workflow "
                    "status before closing the exception."
                )

            return "\n".join(lines)

        # =================================================
        # RECONCILIATION EXCEPTION ANALYSIS
        # =================================================

        if (
            "why are there reconciliation exceptions"
            in q
            or "why reconciliation exceptions"
            in q
            or "why are there exceptions"
            in q
            or "reason for reconciliation exceptions"
            in q
            or "cause of reconciliation exceptions"
            in q
            or "why reconciliation is failing"
            in q
            or "why are transactions unmatched"
            in q
        ):

            exceptions_list = [
                r
                for r in reconciliation_records
                if r.get(
                    "reconciliation_status"
                ) != "MATCHED"
            ]

            exception_count = len(
                exceptions_list
            )

            total_variance = sum(
                abs(
                    float(
                        r.get(
                            "variance",
                            0
                        )
                        or 0
                    )
                )
                for r in exceptions_list
            )

            status_counts = {}

            for r in exceptions_list:

                status = r.get(
                    "reconciliation_status",
                    "UNKNOWN"
                )

                status_counts[status] = (
                    status_counts.get(
                        status,
                        0
                    ) + 1
                )

            reasons = {}

            for r in exceptions_list:

                reason = r.get(
                    "reason"
                )

                if reason:
                    reasons[reason] = (
                        reasons.get(
                            reason,
                            0
                        ) + 1
                    )

            lines = [
                "Reconciliation Exception Analysis",
                "",
                "Current control position:",
                f"• Total transactions: "
                f"{total_transactions:,}",
                f"• Reconciliation rate: "
                f"{reconciliation:.2f}%",
                f"• Unresolved exceptions: "
                f"{exception_count}",
                f"• Total exception variance: "
                f"{total_variance:,.2f} {currency}",
            ]

            if status_counts:

                lines.extend([
                    "",
                    "Exception status breakdown:",
                ])

                for status, count in sorted(
                    status_counts.items()
                ):
                    lines.append(
                        f"• {status}: {count}"
                    )

            if reasons:

                lines.extend([
                    "",
                    "Observed exception reasons:",
                ])

                for reason, count in sorted(
                    reasons.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]:

                    lines.append(
                        f"• {reason}: {count}"
                    )

            grouped = {}

            for r in exceptions_list:
                reason = r.get(
                    "reason"
                )
                category = _cause_category(
                    reason
                )
                grouped[category] = (
                    grouped.get(
                        category,
                        0
                    ) + 1
                )

            if grouped:
                lines.extend([
                    "",
                    "Exception cause grouping:",
                ])
                for category, count in sorted(
                    grouped.items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    if count > 0:
                        lines.append(
                            f"• {category}: {count}"
                        )

            lines.extend([
                "",
                "Why exceptions occur:",
                "• Transaction amounts may differ from "
                "settlement amounts.",
                "• Settlement deductions, including fees, "
                "can create financial variances.",
                "• Timing or settlement-batch differences "
                "can require manual investigation.",
                "• Exceptions remain unresolved until the "
                "supporting transaction and settlement "
                "evidence is reviewed.",
                "",
                "Controller interpretation:",
            ])

            if exception_count == 0:

                lines.append(
                    "• No unresolved reconciliation "
                    "exceptions are currently present."
                )

            else:

                lines.extend([
                    f"• {exception_count} transactions "
                    "require reconciliation attention.",
                    "• The financial impact should be "
                    "prioritized using variance size.",
                    "• Exception reasons should be "
                    "validated against settlement evidence "
                    "before approval or resolution.",
                ])

            lines.extend([
                "",
                "Controller action:",
                "• Prioritize the largest financial "
                "variances first.",
                "• Investigate transaction-versus-settlement "
                "differences.",
                "• Review fee and settlement deductions.",
                "• Resolve exceptions through the Review "
                "Queue and maintain the audit trail.",
            ])

            return "\n".join(lines)

        # =================================================
        # ALL RECONCILIATION EXCEPTIONS
        # =================================================

        if (
            (
                "exception" in q
                or "exceptions" in q
                or "mismatch" in q
                or "mismatches" in q
            )
            and (
                "all" in q
                or "every" in q
                or "list all" in q
                or "show all" in q
                or "complete list" in q
                or "28" in q
            )
        ):

            exceptions = [
                r
                for r in reconciliation_records
                if r.get(
                    "reconciliation_status"
                ) != "MATCHED"
            ]

            exceptions = sorted(
                exceptions,
                key=lambda x: abs(
                    float(
                        x.get(
                            "variance",
                            0
                        )
                        or 0
                    )
                ),
                reverse=True,
            )

            if not exceptions:
                return (
                    "No reconciliation exceptions "
                    "are currently present."
                )

            lines = [
                "Complete Reconciliation Exception List",
                "",
                f"Total exceptions: "
                f"{len(exceptions)}",
                "",
            ]

            for i, r in enumerate(
                exceptions,
                start=1
            ):

                lines.append(
                    f"{i}. "
                    f"{r.get('transaction_id')}"
                )

                lines.append(
                    f"   Status: "
                    f"{r.get('reconciliation_status')}"
                )

                lines.append(
                    f"   Variance: "
                    f"{r.get('variance', 0):,.2f} "
                    f"{r.get('currency', currency)}"
                )

                if r.get("reason"):
                    lines.append(
                        f"   Reason: "
                        f"{r.get('reason')}"
                    )

                lines.append(
                    f"   Review: "
                    f"{r.get('review_status', 'NOT_QUEUED')}"
                )

                if r.get("merchant"):
                    lines.append(
                        f"   Merchant: "
                        f"{r.get('merchant')}"
                    )

                if r.get("vendor"):
                    lines.append(
                        f"   Vendor: "
                        f"{r.get('vendor')}"
                    )

                lines.append("")

            lines.append(
                "Controller recommendation: "
                "Prioritize the largest financial "
                "variances first and investigate "
                "their supporting settlement evidence."
            )

            return "\n".join(lines)

        # =================================================
        # LARGEST RECONCILIATION EXCEPTION
        # =================================================

        largest_requested = (
            "largest" in q
            or "biggest" in q
            or "highest variance" in q
            or "largest variance" in q
            or "top exception" in q
            or "most material" in q
            or "most severe" in q
        )

        if (
            largest_requested
            and (
                "exception" in q
                or "exceptions" in q
                or "mismatch" in q
                or "mismatches" in q
                or "variance" in q
            )
        ):

            exceptions = [
                r
                for r in reconciliation_records
                if r.get(
                    "reconciliation_status"
                ) != "MATCHED"
            ]

            if not exceptions:
                return (
                    "No reconciliation exceptions "
                    "are currently present. Nothing "
                    "requires prioritization right now."
                )

            top_exception = max(
                exceptions,
                key=lambda x: abs(
                    float(
                        x.get(
                            "variance",
                            0
                        )
                        or 0
                    )
                )
            )

            lines = [
                "Largest Reconciliation Exception",
                "",
                f"• Transaction: "
                f"{top_exception.get('transaction_id')}",
                f"• Variance: "
                f"{top_exception.get('variance', 0):,.2f} "
                f"{top_exception.get('currency', currency)}",
                f"• Status: "
                f"{top_exception.get('reconciliation_status', 'UNKNOWN')}",
                f"• Review status: "
                f"{top_exception.get('review_status', 'NOT_QUEUED')}",
            ]

            if (
                top_exception.get(
                    "amount"
                ) is not None
            ):
                lines.append(
                    f"• Amount: "
                    f"{top_exception.get('amount'):,.2f} "
                    f"{top_exception.get('currency', currency)}"
                )

            if (
                top_exception.get(
                    "settlement_amount"
                ) is not None
            ):
                lines.append(
                    f"• Settlement amount: "
                    f"{top_exception.get('settlement_amount'):,.2f} "
                    f"{top_exception.get('currency', currency)}"
                )

            if top_exception.get(
                "risk_level"
            ):
                lines.append(
                    f"• Risk level: "
                    f"{top_exception.get('risk_level')} "
                    f"({top_exception.get('risk_score', 0):.0f}/100)"
                )
            else:
                lines.append(
                    "• Risk level: Not assessed"
                )

            factors = top_exception.get(
                "risk_factors",
                []
            )

            if factors:
                if isinstance(
                    factors,
                    list
                ):
                    factor_text = ", ".join(
                        str(x)
                        for x in factors
                    )
                else:
                    factor_text = str(
                        factors
                    )
                lines.append(
                    f"• Risk factors: "
                    f"{factor_text}"
                )

            if top_exception.get(
                "reason"
            ):
                lines.append(
                    f"• Reason: "
                    f"{top_exception.get('reason')}"
                )

            lines.extend([
                "",
                "Recommended controller action:",
                f"Investigate {top_exception.get('transaction_id')} "
                "first - verify the transaction against settlement "
                "evidence, then approve, resolve, or escalate it in "
                "the Review Center with an audit note.",
            ])

            return "\n".join(lines)

        # =================================================
        # PRIORITY RECONCILIATION EXCEPTIONS
        # =================================================

        if (
            (
                "exception" in q
                or "exceptions" in q
                or "mismatch" in q
                or "mismatches" in q
            )
            and (
                "which" in q
                or "prioritize" in q
                or "first" in q
                or "review" in q
            )
        ):

            exceptions = [
                r
                for r in reconciliation_records
                if r.get(
                    "reconciliation_status"
                ) != "MATCHED"
            ]

            exceptions = sorted(
                exceptions,
                key=lambda x: abs(
                    float(
                        x.get(
                            "variance",
                            0
                        )
                        or 0
                    )
                ),
                reverse=True,
            )

            if not exceptions:
                return (
                    "No reconciliation exceptions "
                    "are currently present."
                )

            limit = 10

            lines = [
                "Priority Exception Review",
                "",
                f"Total exceptions: "
                f"{len(exceptions)}",
                "",
            ]

            for i, r in enumerate(
                exceptions[:limit],
                start=1
            ):

                lines.append(
                    f"{i}. "
                    f"{r.get('transaction_id')}"
                )

                lines.append(
                    f"   Status: "
                    f"{r.get('reconciliation_status')}"
                )

                lines.append(
                    f"   Variance: "
                    f"{r.get('variance', 0):,.2f} "
                    f"{r.get('currency', currency)}"
                )

                if r.get("reason"):
                    lines.append(
                        f"   Reason: "
                        f"{r.get('reason')}"
                    )

                lines.append(
                    f"   Review: "
                    f"{r.get('review_status', 'NOT_QUEUED')}"
                )
                if r.get("risk_level"):
                    lines.append(
                        f"   Risk: "
                        f"{r.get('risk_level')}"
                    )


                if r.get("merchant"):
                    lines.append(
                        f"   Merchant: "
                        f"{r.get('merchant')}"
                    )

                lines.append("")

            if limit < len(exceptions):

                lines.append(
                    f"Showing top {limit} of "
                    f"{len(exceptions)} exceptions. "
                    f"Ask 'show all exceptions' "
                    f"to see the complete list."
                )

                lines.append("")

            lines.extend([
                "",
                "Recommended first action:",
                f"Investigate {exceptions[0].get('transaction_id')} "
                f"- the largest exception with "
                f"{exceptions[0].get('variance', 0):,.2f} "
                f"{exceptions[0].get('currency', currency)} "
                "variance"
                + (
                    f" ({exceptions[0].get('risk_level')} risk)."
                    if exceptions[0].get("risk_level")
                    else "."
                ),
            ])

            lines.append(
                "Controller recommendation: "
                "Prioritize exceptions with the "
                "largest financial variance first, "
                "then investigate settlement "
                "evidence and review status."
            )

            return "\n".join(lines)

        # =================================================
        # ACTUAL HIGH-RISK TRANSACTIONS
        # =================================================

        if (
            (
                "risk" in q
                or "high-risk" in q
                or "high risk" in q
            )
            and (
                "which" in q
                or "show" in q
                or "prioritize" in q
                or "transaction" in q
            )
        ):

            risks = sorted(
                risk_records,
                key=lambda x: float(
                    x.get(
                        "risk_score",
                        0
                    )
                    or 0
                ),
                reverse=True,
            )

            if not risks:
                return (
                    "No risk assessment records "
                    "are currently available."
                )

            show_all = (
                "all" in q
                or "every" in q
                or "show all" in q
            )

            limit = (
                len(risks)
                if show_all
                else 10
            )

            lines = [
                "Priority Risk Review",
                "",
                f"Risk records available: "
                f"{len(risks)}",
                "",
            ]

            for i, r in enumerate(
                risks[:limit],
                start=1
            ):

                lines.append(
                    f"{i}. "
                    f"{r.get('transaction_id')}"
                )

                lines.append(
                    f"   Risk score: "
                    f"{r.get('risk_score', 0):.2f}"
                )

                lines.append(
                    f"   Risk level: "
                    f"{r.get('risk_level', 'UNKNOWN')}"
                )

                factors = r.get(
                    "risk_factors",
                    []
                )

                if factors:

                    if isinstance(
                        factors,
                        list
                    ):
                        factor_text = ", ".join(
                            str(x)
                            for x in factors
                        )
                    else:
                        factor_text = str(
                            factors
                        )

                    lines.append(
                        f"   Factors: "
                        f"{factor_text}"
                    )

                lines.append("")

            if limit < len(risks):

                lines.append(
                    f"Showing top {limit} risk records. "
                    f"Ask 'show all high-risk transactions' "
                    f"for the complete list."
                )

                lines.append("")

            lines.append(
                "Controller recommendation: "
                "Start with the highest risk score, "
                "verify the listed risk factors, and "
                "escalate material cases when necessary."
            )

            return "\n".join(lines)

        # =================================================
        # REVIEW QUEUE STATUS
        # =================================================

        if (
            "review queue" in q
            or (
                "review" in q
                and (
                    "open" in q
                    or "pending" in q
                    or "status" in q
                )
            )
        ):

            if not review_records:
                return (
                    "The review queue is currently empty."
                )

            status_counts = {}

            for r in review_records:

                status = r.get(
                    "status",
                    "UNKNOWN"
                )

                status_counts[status] = (
                    status_counts.get(
                        status,
                        0
                    ) + 1
                )

            lines = [
                "Review Queue Status",
                "",
                f"Total review items: "
                f"{len(review_records)}",
                "",
            ]

            for status, count in sorted(
                status_counts.items()
            ):

                lines.append(
                    f"• {status}: {count}"
                )

            open_items = [
                r
                for r in review_records
                if r.get("status")
                in [
                    "OPEN",
                    "UNDER_REVIEW",
                    "ESCALATED",
                ]
            ]

            if open_items:

                lines.extend([
                    "",
                    "Controller action:",
                    f"{len(open_items)} items "
                    "still require attention."
                ])

            return "\n".join(lines)

        # =================================================
        # AI CONTROLLER ACTION ENGINE
        # =================================================

        action_plan_requested = (
            "what should i do first" in q
            or "what should i do" in q
            or "most urgent finance issues" in q
            or "most urgent financial issues" in q
            or "urgent finance issues" in q
            or "urgent financial issues" in q
            or "today's controller action plan" in q
            or "todays controller action plan" in q
            or "today controller action plan" in q
            or "controller action plan" in q
            or "finance action plan" in q
        )

        if action_plan_requested:

            exceptions = [
                r
                for r in reconciliation_records
                if r.get(
                    "reconciliation_status"
                ) != "MATCHED"
            ]

            unresolved_reviews = [
                r
                for r in review_records
                if r.get("status")
                in [
                    "OPEN",
                    "UNDER_REVIEW",
                    "ESCALATED",
                ]
            ]

            priority_exceptions = sorted(
                exceptions,
                key=lambda x: abs(
                    float(
                        x.get(
                            "variance",
                            0
                        )
                        or 0
                    )
                ),
                reverse=True,
            )

            lines = [
                "AI CONTROLLER ACTION PLAN",
                "",
                "CONTROL SNAPSHOT",
                f"• Total transactions: "
                f"{total_transactions:,}",
                f"• Reconciliation rate: "
                f"{reconciliation:.2f}%",
                f"• Unresolved reconciliation exceptions: "
                f"{len(exceptions)}",
                f"• Review items requiring attention: "
                f"{len(unresolved_reviews)}",
                f"• High-risk transactions: "
                f"{high_risk}",
                f"• Net profit: "
                f"{net_profit:,.2f} {currency}",
                f"• Cash balance: "
                f"{cash_balance:,.2f} {currency}",
                "",
                "PRIORITY 1 — RECONCILIATION",
            ]

            if priority_exceptions:

                top_exception = priority_exceptions[0]

                lines.extend([
                    f"• Highest variance transaction: "
                    f"{top_exception.get('transaction_id')}",
                    f"• Variance: "
                    f"{top_exception.get('variance', 0):,.2f} "
                    f"{top_exception.get('currency', currency)}",
                    f"• Status: "
                    f"{top_exception.get('reconciliation_status', 'UNKNOWN')}",
                    f"• Risk level: "
                    f"{top_exception.get('risk_level', 'Not assessed')}",
                    "",
                    "Recommended action:",
                    "Investigate the highest-variance "
                    "settlement exception first and verify "
                    "the transaction against settlement evidence.",
                ])

            else:

                lines.extend([
                    "• No unresolved reconciliation "
                    "exceptions are currently reported.",
                    "• Continue routine reconciliation monitoring.",
                ])

            lines.extend([
                "",
                "PRIORITY 2 — RISK",
            ])

            if high_risk > 0:

                lines.extend([
                    f"• {high_risk} high-risk transaction(s) "
                    "require review.",
                    "• Start with the highest risk score.",
                    "• Verify risk factors before approval "
                    "or escalation.",
                ])

            else:

                lines.extend([
                    "• No high-risk transactions are "
                    "currently reported.",
                    "• Continue monitoring risk assessments.",
                ])

            lines.extend([
                "",
                "PRIORITY 3 — REVIEW WORKFLOW",
            ])

            if unresolved_reviews:

                lines.extend([
                    f"• {len(unresolved_reviews)} review item(s) "
                    "remain active.",
                    "• Complete investigation before "
                    "marking exceptions resolved.",
                    "• Maintain the audit trail for every "
                    "controller decision.",
                ])

            else:

                lines.extend([
                    "• No active review items currently "
                    "require controller attention."
                ])

            lines.extend([
                "",
                "PRIORITY 4 — PROFITABILITY",
                f"• Revenue: "
                f"{revenue:,.2f} {currency}",
                f"• Expenses: "
                f"{expenses:,.2f} {currency}",
                f"• Net profit: "
                f"{net_profit:,.2f} {currency}",
                f"• Profit margin: "
                f"{profit_margin:.2f}%",
            ])

            if net_profit < 0:

                lines.extend([
                    "• Profitability is under pressure "
                    "because net profit is negative.",
                    "• Review controllable expenses, "
                    "refunds, and fees.",
                ])

            else:

                lines.extend([
                    "• Profitability is currently positive.",
                    "• Continue monitoring expense, refund, "
                    "and fee trends."
                ])

            lines.extend([
                "",
                "TODAY'S RECOMMENDED SEQUENCE",
                "1. Open Review Center.",
                "2. Investigate the highest-variance "
                "reconciliation exception.",
                "3. Review the highest-risk transactions.",
                "4. Resolve or escalate active review items.",
                "5. Review profitability pressure and "
                "controllable costs.",
                "6. Record material decisions in the "
                "audit trail.",
                "",
                "CONTROLLER DECISION",
                "Start with reconciliation exceptions "
                "because they directly affect the reliability "
                "of settlement and cash information."
            ])

            return "\n".join(lines)

        # =================================================
        # WHY IS THE RECONCILIATION RATE BELOW 100%
        # =================================================

        rate_below_requested = (
            "below 100" in q
            or ("reconciliation" in q and "below" in q)
            or ("match rate" in q and "below" in q)
        )

        if rate_below_requested:

            matched_count = sum(
                1
                for r in reconciliation_records
                if r.get("reconciliation_status")
                == "MATCHED"
            )

            exception_items = [
                r
                for r in reconciliation_records
                if r.get("reconciliation_status")
                != "MATCHED"
            ]

            exception_variance = sum(
                abs(
                    float(
                        r.get(
                            "variance",
                            0
                        )
                        or 0
                    )
                )
                for r in exception_items
            )

            if not exception_items:

                return (
                    "Reconciliation rate analysis:\n\n"
                    f"• Current reconciliation rate: "
                    f"{reconciliation:.1f}%\n"
                    "• Every transaction in the current run "
                    "is matched.\n\n"
                    "There are no unresolved exceptions, so "
                    "the rate is already at its ceiling."
                )

            lines = [
                "Reconciliation Rate Analysis",
                "",
                f"• Current reconciliation rate: "
                f"{reconciliation:.1f}%",
                f"• Matched transactions: "
                f"{matched_count}",
                f"• Unresolved exceptions: "
                f"{len(exception_items)}",
                f"• Total exception variance: "
                f"{exception_variance:,.2f} {currency}",
                "",
                "Why the rate is below 100%:",
                "• Every unresolved exception lowers the "
                "match rate.",
                "• Exceptions exist because the transaction "
                "and settlement evidence does not fully agree "
                "within the configured tolerance.",
                "",
                "Recommended first action:",
                "Review the highest-variance exceptions first, "
                "verify the settlement evidence, and resolve "
                "them through the Review Center.",
            ]

            return "\n".join(lines)

        # =================================================
        # SUMMARIZE CURRENT RECONCILIATION RUN
        # =================================================

        if (
            "summarize" in q
            and (
                "reconciliation" in q
                or "run" in q
                or "current" in q
            )
        ):

            run_summary = k.get(
                "reconciliation",
                {}
            )

            run_meta = k.get(
                "current_run"
            ) or {}

            current_files = (
                run_meta.get("files")
                or []
            )

            if not run_summary.get(
                "run_id"
            ):

                return (
                    "Current Reconciliation Run Summary\n\n"
                    "No reconciliation run is available yet. "
                    "Upload finance data on the Reconciliation "
                    "page to generate a current run summary."
                )

            lines = [
                "Current Reconciliation Run Summary",
                "",
                f"• Run ID: "
                f"{run_summary.get('run_id')}",
                f"• Mode: "
                f"{(run_summary.get('mode') or 'reconciliation').replace('_', ' ')}",
            ]

            if current_files:

                lines.append(
                    f"• Source files: "
                    f"{', '.join(current_files)}"
                )

            lines.extend([
                f"• Total transactions: "
                f"{run_summary.get('total', 0)}",
                f"• Matched: "
                f"{run_summary.get('matched', 0)}",
                f"• Unresolved exceptions: "
                f"{run_summary.get('exceptions', 0)}",
                f"• Match rate: "
                f"{float(run_summary.get('match_rate') or 0):.1f}%",
                f"• Total variance: "
                f"{float(run_summary.get('variance') or 0):,.2f} {currency}",
                "",
            ])

            top = (
                k.get("top_exceptions")
                or []
            )[:1]

            if top:

                lines.extend([
                    "Largest exception:",
                    f"• {top[0].get('transaction_id')} - "
                    f"{float(top[0].get('variance') or 0):,.2f} "
                    f"{currency}",
                    "",
                ])

            lines.append(
                "Recommended next step: review the highest-variance "
                "exceptions in the Review Center before closing the run."
            )

            return "\n".join(lines)

        # =================================================
        # WHAT CHANGED IN THE LATEST UPLOAD
        # =================================================

        if (
            "what changed" in q
            or "latest upload" in q
            or (
                "changed" in q
                and "upload" in q
            )
        ):

            current = k.get(
                "reconciliation",
                {}
            )

            previous = k.get(
                "previous_reconciliation"
            )

            meta = k.get(
                "current_run"
            ) or {}

            files = meta.get("files") or []

            if not current.get("run_id"):

                return (
                    "No reconciliation run has been completed yet, "
                    "so there is no upload change to report. Upload "
                    "finance data to start a reconciliation run."
                )

            lines = [
                "Latest Upload Summary",
                "",
                f"• Current run: "
                f"{current.get('run_id')}",
            ]

            if files:

                lines.append(
                    f"• Current files: "
                    f"{', '.join(files)}"
                )

            lines.extend([
                f"• Total transactions: "
                f"{current.get('total', 0)}",
                f"• Matched: "
                f"{current.get('matched', 0)}",
                f"• Exceptions: "
                f"{current.get('exceptions', 0)}",
                f"• Match rate: "
                f"{float(current.get('match_rate') or 0):.1f}%",
                f"• Total variance: "
                f"{float(current.get('variance') or 0):,.2f} {currency}",
                "",
            ])

            if previous:

                previous_files = (
                    previous.get("files")
                    or []
                )

                lines.extend([
                    "Compared with the previous run:",
                    f"• Previous run: "
                    f"{previous.get('run_id')}",
                ])

                if previous_files:

                    lines.append(
                        f"• Previous files: "
                        f"{', '.join(previous_files)}"
                    )

                lines.append(
                    f"• Previous totals: "
                    f"{previous.get('total', 0)} transactions, "
                    f"{previous.get('matched', 0)} matched, "
                    f"{previous.get('exceptions', 0)} exceptions, "
                    f"{float(previous.get('match_rate') or 0):.1f}% "
                    f"match rate, variance "
                    f"{float(previous.get('variance') or 0):,.2f} "
                    f"{currency}"
                )

            else:

                lines.append(
                    "• Previous run: none - this is the first "
                    "reconciliation run in the workspace."
                )

            lines.extend([
                "",
                "The Overview, Risk, Anomaly, and Review views now "
                "reflect this current run. Review unresolved "
                "exceptions before closing the run.",
            ])

            return "\n".join(lines)

        # =================================================
        # SCENARIO ANALYSIS
        # =================================================

        scenario_requested = (
            "scenario" in q
            or "drop 10" in q
            or "10%" in q
            or "10 percent" in q
            or "decrease revenue" in q
            or "reduce revenue" in q
            or "revenue drops" in q
            or "revenue drop" in q
            or "revenue falls" in q
            or "revenue decline" in q
        )

        if scenario_requested:

            revenue_change = -10.0

            current_revenue = revenue
            current_expenses = expenses
            current_refunds = refunds
            current_fees = fees

            current_operating_profit = (
                current_revenue
                - current_expenses
            )

            calculated_current_net_profit = (
                current_operating_profit
                - current_refunds
                - current_fees
            )

            projected_revenue = (
                current_revenue
                * (1 + revenue_change / 100)
            )

            projected_expenses = current_expenses
            projected_refunds = current_refunds
            projected_fees = current_fees

            projected_operating_profit = (
                projected_revenue
                - projected_expenses
            )

            projected_net_profit = (
                projected_operating_profit
                - projected_refunds
                - projected_fees
            )

            profit_impact = (
                projected_net_profit
                - calculated_current_net_profit
            )

            # Simplified modeled cash impact.
            # This is not a full cash-flow calculation.
            cash_impact = profit_impact

            projected_margin = (
                (
                    projected_net_profit
                    / projected_revenue
                )
                * 100
                if projected_revenue
                else 0
            )

            revenue_reduction = (
                current_revenue
                - projected_revenue
            )

            net_profit_difference = (
                calculated_current_net_profit
                - net_profit
            )

            lines = [
                "Revenue Downside Scenario",
                "",
                "Assumption:",
                "• Revenue decreases by 10%",
                "• Expenses, refunds and fees remain unchanged",
                "",
                "Current financial position:",
                f"• Revenue: "
                f"{current_revenue:,.2f} {currency}",
                f"• Expenses: "
                f"{current_expenses:,.2f} {currency}",
                f"• Refunds: "
                f"{current_refunds:,.2f} {currency}",
                f"• Fees: "
                f"{current_fees:,.2f} {currency}",
                f"• Current operating profit: "
                f"{current_operating_profit:,.2f} {currency}",
                f"• Current net profit: "
                f"{calculated_current_net_profit:,.2f} {currency}",
                "",
                "Projected financial position:",
                f"• Revenue reduction: "
                f"{revenue_reduction:,.2f} {currency}",
                f"• Projected revenue: "
                f"{projected_revenue:,.2f} {currency}",
                f"• Projected expenses: "
                f"{projected_expenses:,.2f} {currency}",
                f"• Projected refunds: "
                f"{projected_refunds:,.2f} {currency}",
                f"• Projected fees: "
                f"{projected_fees:,.2f} {currency}",
                f"• Projected operating profit: "
                f"{projected_operating_profit:,.2f} {currency}",
                f"• Projected net profit: "
                f"{projected_net_profit:,.2f} {currency}",
                f"• Projected profit margin: "
                f"{projected_margin:.2f}%",
                "",
                "Impact analysis:",
                f"• Exact profit impact: "
                f"{profit_impact:,.2f} {currency}",
                f"• Estimated cash impact: "
                f"{cash_impact:,.2f} {currency}",
            ]

            if abs(net_profit_difference) > 0.01:

                lines.extend([
                    "",
                    "Data consistency notice:",
                    f"• Application net profit: "
                    f"{net_profit:,.2f} {currency}",
                    f"• Calculated net profit from "
                    f"revenue/expenses/refunds/fees: "
                    f"{calculated_current_net_profit:,.2f} {currency}",
                    f"• Difference: "
                    f"{net_profit_difference:,.2f} {currency}",
                    "• The scenario calculation uses the "
                    "explicit revenue, expense, refund, and "
                    "fee components shown above.",
                ])

            if projected_net_profit < 0:

                lines.extend([
                    "",
                    "Controller interpretation:",
                    "• The business remains loss-making "
                    "under the 10% revenue downside scenario.",
                    "• Operating profit deteriorates because "
                    "expenses are held constant while revenue falls.",
                    "• Refunds and fees are explicitly included "
                    "in the final net-profit calculation.",
                ])

            else:

                lines.extend([
                    "",
                    "Controller interpretation:",
                    "• The business remains profitable under "
                    "the 10% revenue downside scenario.",
                    "• Operating profit decreases because "
                    "expenses are held constant while revenue falls.",
                    "• Refunds and fees are explicitly included "
                    "in the final net-profit calculation.",
                ])

            lines.extend([
                "",
                "Controller action:",
                "• Review discretionary expenses.",
                "• Monitor refund and fee exposure.",
                "• Investigate reconciliation exceptions "
                "affecting cash realization.",
                "• Test additional revenue and expense "
                "assumptions in the Scenario Simulator.",
            ])

            return "\n".join(lines)

        # =================================================
        # REVENUE
        # =================================================

        if "revenue" in q:

            return (
                f"Revenue analysis:\n\n"
                f"• Revenue: "
                f"{revenue:,.2f} {currency}\n"
                f"• Transactions: "
                f"{total_transactions:,}\n\n"
                f"Revenue should be evaluated together "
                f"with expenses, refunds, fees, and "
                f"transaction volume before drawing "
                f"conclusions about financial performance."
            )

        # =================================================
        # EXPENSE
        # =================================================

        if (
            "expense" in q
            or "expenses" in q
        ):

            return (
                f"Expense analysis:\n\n"
                f"• Expenses: "
                f"{expenses:,.2f} {currency}\n"
                f"• Refunds: "
                f"{refunds:,.2f} {currency}\n"
                f"• Fees: "
                f"{fees:,.2f} {currency}\n\n"
                f"Controller action:\n"
                f"Review the largest expense categories "
                f"and investigate unusual increases "
                f"before attributing causes."
            )

        # =================================================
        # PROFIT / MARGIN
        # =================================================

        if (
            "profit" in q
            or "margin" in q
            or "profitable" in q
        ):

            return (
                f"Profitability analysis:\n\n"
                f"• Revenue: "
                f"{revenue:,.2f} {currency}\n"
                f"• Expenses: "
                f"{expenses:,.2f} {currency}\n"
                f"• Net profit: "
                f"{net_profit:,.2f} {currency}\n"
                f"• Profit margin: "
                f"{profit_margin:.2f}%\n\n"
                f"Controller view:\n"
                f"Monitor expense growth, refunds, "
                f"and fees alongside revenue to "
                f"understand changes in profitability."
            )

        # =================================================
        # CASH / LIQUIDITY
        # =================================================

        if (
            "cash" in q
            or "liquidity" in q
        ):

            return (
                f"Cash & liquidity analysis:\n\n"
                f"• Cash balance: "
                f"{cash_balance:,.2f} {currency}\n"
                f"• Revenue: "
                f"{revenue:,.2f} {currency}\n"
                f"• Expenses: "
                f"{expenses:,.2f} {currency}\n\n"
                f"Controller action:\n"
                f"Monitor cash movements, upcoming "
                f"obligations, refund exposure, and "
                f"settlement timing.\n\n"
                f"Note: a complete liquidity assessment "
                f"requires balance-sheet and "
                f"payable/receivable data that may "
                f"not be present in the source dataset."
            )

        # =================================================
        # REFUNDS
        # =================================================

        if "refund" in q:

            return (
                f"Refund analysis:\n\n"
                f"• Refund amount: "
                f"{refunds:,.2f} {currency}\n\n"
                f"Review unusual refund concentrations, "
                f"repeated refund activity, and "
                f"transactions with unusually large "
                f"refund values."
            )

        # =================================================
        # FEES
        # =================================================

        if (
            "fee" in q
            or "fees" in q
        ):

            return (
                f"Fee analysis:\n\n"
                f"• Fees: "
                f"{fees:,.2f} {currency}\n\n"
                f"Compare fee levels against transaction "
                f"volume and revenue to identify "
                f"unusual changes."
            )

        # =================================================
        # CFO SUMMARY
        # =================================================

        if (
            "cfo" in q
            or "summary" in q
            or "executive" in q
        ):

            high_risk_action = (
                "No high-risk transactions are currently "
                "reported; continue monitoring risk assessments."
                if high_risk == 0
                else
                "Review high-risk transactions first."
            )

            return (
                f"CFO executive summary:\n\n"
                f"• Revenue: "
                f"{revenue:,.2f} {currency}\n"
                f"• Expenses: "
                f"{expenses:,.2f} {currency}\n"
                f"• Net profit: "
                f"{net_profit:,.2f} {currency}\n"
                f"• Profit margin: "
                f"{profit_margin:.2f}%\n"
                f"• Cash balance: "
                f"{cash_balance:,.2f} {currency}\n"
                f"• Reconciliation: "
                f"{reconciliation:.1f}%\n"
                f"• High-risk transactions: "
                f"{high_risk}\n\n"
                f"Priority actions:\n"
                f"1. {high_risk_action}\n"
                f"2. Investigate reconciliation exceptions.\n"
                f"3. Monitor liquidity and cash movements.\n"
                f"4. Investigate material expense, "
                f"refund, and fee anomalies.\n\n"
                f"All quantitative figures above are based "
                f"on the application's structured "
                f"finance context."
            )

        # =================================================
        # CURRENT RATIO / UNSUPPORTED ACCOUNTING DATA
        # =================================================

        if (
            "current ratio" in q
            or "balance sheet" in q
            or "liabilities" in q
        ):

            return (
                "Insufficient source data.\n\n"
                "The current application dataset does not "
                "fully represent current assets and current "
                "liabilities, so a reliable accounting ratio "
                "cannot be calculated."
            )

        # =================================================
        # DEFAULT RESPONSE
        # =================================================

        return (
            f"I analyzed the application's structured "
            f"finance context.\n\n"
            f"• Revenue: "
            f"{revenue:,.2f} {currency}\n"
            f"• Expenses: "
            f"{expenses:,.2f} {currency}\n"
            f"• Net profit: "
            f"{net_profit:,.2f} {currency}\n"
            f"• Cash balance: "
            f"{cash_balance:,.2f} {currency}\n"
            f"• Reconciliation: "
            f"{reconciliation:.1f}%\n"
            f"• High-risk transactions: "
            f"{high_risk}\n\n"
            f"For accounting information not supported "
            f"by the source data, I will explicitly state: "
            f"Insufficient source data."
        )


class ExternalAIProvider(AIProvider):

    def __init__(self, api_key):
        self.api_key = api_key

    def answer(self, question, context):
        return (
            "External provider is configured as an "
            "extension point; the default application "
            "remains in Mock AI mode."
        )


def get_provider(name, key=None):

    if name == "external" and key:
        return ExternalAIProvider(key)

    return MockAIProvider()