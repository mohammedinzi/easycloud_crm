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

(function () {
	const CARD_ICONS = {
		"Total Leads": "icon-users",
		"Open Deals": "icon-sell",
		"Won Deals": "icon-check",
		Revenue: "icon-money-coins-1",
		Projects: "icon-projects",
		"Lost Deals": "icon-close",
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
		if (!icon_name) return;

		const extra_class = label === "Lost Deals" ? "ec-card-icon-lost" : "";
		titleEl.insertAdjacentHTML("afterbegin", icon_svg(icon_name, extra_class));
	}

	function scan(root) {
		root.querySelectorAll &&
			root.querySelectorAll(".number-widget-box").forEach(add_icon_to_card);
	}

	const observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			mutation.addedNodes.forEach((node) => {
				if (node.nodeType !== 1) return;
				if (node.classList && node.classList.contains("number-widget-box")) {
					add_icon_to_card(node);
				}
				scan(node);
			});
		}
	});

	observer.observe(document.body, { childList: true, subtree: true });

	// in case any cards are already on the page by the time this runs
	scan(document.body);
})();
