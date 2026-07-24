// ====================================================================
// SECTION: BUSINESS LIST FILTERING + PAGINATION
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBusinessListFilters(...).
// ====================================================================

export const businessListState = {
  parties: {
    offset: 0,
    q: "",
    party_type: "",
    from_date: "",
    to_date: "",
  },
  vouchers: {
    offset: 0,
    voucher_type: "",
    status: "",
    approval_status: "",
    include_reviewed: false,
  },
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initBusinessListFilters(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBusinessListFilters() must be called before using business list filter helpers");
  }
  return deps;
}

function loadBusinessParties() { return requireDeps().loadBusinessParties(); }
function loadBusinessVouchers() { return requireDeps().loadBusinessVouchers(); }

export function applyBusinessListFilter(listKind) {
  if (listKind === "parties") {
    const panel = document.querySelector("[data-business-list='parties']");
    if (!panel) return;

    const qInput = panel.querySelector("input[name='q']");
    const typeInput = panel.querySelector("select[name='party_type']");

    businessListState.parties.q = qInput?.value || "";
    businessListState.parties.party_type = typeInput?.value || "";
    businessListState.parties.offset = 0;

    loadBusinessParties();
  } else if (listKind === "vouchers") {
    const panel = document.querySelector("[data-business-list='vouchers']");
    if (!panel) return;

    const voucherTypeInput = panel.querySelector("select[name='voucher_type']");
    const statusInput = panel.querySelector("select[name='status']");
    const approvalInput = panel.querySelector("select[name='approval_status']");

    businessListState.vouchers.voucher_type = voucherTypeInput?.value || "";
    businessListState.vouchers.status = statusInput?.value || "";
    businessListState.vouchers.approval_status = approvalInput?.value || "";
    businessListState.vouchers.offset = 0;

    loadBusinessVouchers();
  }
}

export function resetBusinessListFilter(listKind) {
  if (listKind === "parties") {
    businessListState.parties = {
      offset: 0,
      q: "",
      party_type: "",
      from_date: "",
      to_date: "",
    };
    loadBusinessParties();
  } else if (listKind === "vouchers") {
    businessListState.vouchers = {
      offset: 0,
      voucher_type: "",
      status: "",
      approval_status: "",
      include_reviewed: false,
    };
    loadBusinessVouchers();
  }
}

export function pageBusinessList(listKind, direction) {
  if (listKind === "parties") {
    const offset = Number(businessListState.parties.offset || 0);
    businessListState.parties.offset = direction === "next" ? offset + 20 : Math.max(0, offset - 20);
    loadBusinessParties();
  } else if (listKind === "vouchers") {
    const offset = Number(businessListState.vouchers.offset || 0);
    businessListState.vouchers.offset = direction === "next" ? offset + 20 : Math.max(0, offset - 20);
    loadBusinessVouchers();
  }
}

