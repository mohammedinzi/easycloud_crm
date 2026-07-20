// ==============================================================================
// public/js/workspace_icons.js -- loaded on EVERY Desk page (see
// hooks.py's app_include_js), but only actually DOES anything on the
// EasyCloud CRM workspace page (everywhere else, scan() below just finds
// nothing matching and the MutationObserver sits idle).
// ==============================================================================
//
// Adds an icon to each easycloud_crm Number Card on the Workspace dashboard,
// reusing Frappe's own bundled SVG icon sprite (apps/frappe/frappe/public/icons/
// timeless/icons.svg, referenced everywhere in Desk via <svg class="icon">
// <use href="#icon-name"></use></svg> -- confirmed this exact pattern in
// frappe/public/js/frappe/views/kanban/kanban_column.html) rather than pulling
// in a new icon set.
//
// Number Card widgets render asynchronously (NumberCardWidget#make_card awaits
// an xcall before building its DOM), and there's no public "card rendered"
// event to hook -- a MutationObserver watching for new .number-widget-box
// nodes is the reliable way to catch them regardless of route-change or
// render timing, rather than guessing at a delay.

// Wrapped in an immediately-invoked function expression so CARD_ICONS,
// icon_svg, etc. stay private to this file and never leak into (or clash
// with) the global scope -- important here specifically because this file
// loads on every single page via app_include_js, unlike a doctype_js file
// that's scoped to one form.
(function () {
	// Maps each Number Card's exact visible title (see
	// ../../easycloud_crm/number_card/*/*.json for each card's own "label")
	// to one of Frappe's own bundled icon names. Any card title NOT listed
	// here simply gets no icon -- see add_icon_to_card's early return below.
	const CARD_ICONS = {
		"Total Leads": "icon-users",
		"Open Leads": "icon-users",
		"Total Deals": "icon-list",
		"Open Deals": "icon-sell",
		"Won Deals": "icon-check",
		Revenue: "icon-money-coins-1",
		"Lost Deals": "icon-close",
		"CRM Activities": "icon-activity",
	};

	function icon_svg(icon_name, extra_class) {
		return `<svg class="icon icon-md ec-card-icon ${extra_class || ""}"><use href="#${icon_name}"></use></svg>`;
	}

	function add_icon_to_card(cardEl) {
		if (cardEl.querySelector(".ec-card-icon")) return; // already done

		const titleEl = cardEl.querySelector(".widget-title");
		if (!titleEl) return;

		const label = titleEl.textContent.trim();
		const icon_name = CARD_ICONS[label];
		if (!icon_name) return; // not one of OUR cards (or a title we don't recognise) -- leave it alone

		// "Lost Deals" gets its own CSS class so it can be coloured red
		// (see easycloud_crm.css) -- every other card just uses the
		// default icon colour.
		const extra_class = label === "Lost Deals" ? "ec-card-icon-lost" : "";
		titleEl.insertAdjacentHTML("afterbegin", icon_svg(icon_name, extra_class));
	}

	function scan(root) {
		root.querySelectorAll &&
			root.querySelectorAll(".number-widget-box").forEach(add_icon_to_card);
	}

	// Watches the ENTIRE page body for any newly-added DOM nodes, forever
	// (this observer is never disconnected) -- necessary because, as the
	// header comment explains, Number Cards render asynchronously with no
	// event to hook into directly, and Frappe is a single-page app where
	// navigating between pages doesn't reload this script, so it has to
	// keep watching for cards appearing on ANY future page too.
	const observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			mutation.addedNodes.forEach((node) => {
				if (node.nodeType !== 1) return; // skip text nodes etc. -- only interested in real elements
				if (node.classList && node.classList.contains("number-widget-box")) {
					add_icon_to_card(node);
				}
				// A card can also arrive already nested inside some larger
				// newly-added chunk of DOM (not necessarily as the direct
				// added node itself) -- scan(node) catches those too.
				scan(node);
			});
		}
	});

	observer.observe(document.body, { childList: true, subtree: true });

	// in case any cards are already on the page by the time this runs
	scan(document.body);
})();
