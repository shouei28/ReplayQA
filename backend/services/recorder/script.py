"""JavaScript injected into the browser to capture click and input events for recording."""

RECORDER_INJECT_SCRIPT_TEMPLATE = """
(function() {
    var __qualty_session_id = "__QUALTY_SESSION_ID__";
    var __qualty_storage_key = "__qualty_pending_" + __qualty_session_id;
    
    // Each run is a fresh document (add_init_script runs on every navigation).
    window.__qualty_actions = [];
    
    // Restore actions from sessionStorage (same-origin navigation: previous page saved before unload).
    try {
        var pending = sessionStorage.getItem(__qualty_storage_key);
        if (pending) {
            var parsed = JSON.parse(pending);
            if (Array.isArray(parsed) && parsed.length > 0) {
                window.__qualty_actions = parsed;
                console.log('[QUALTY RECORDER] Restored', parsed.length, 'pending actions from sessionStorage');
            }
            sessionStorage.removeItem(__qualty_storage_key);
        }
    } catch (e) {
        console.warn('[QUALTY RECORDER] Failed to restore pending actions:', e);
    }
    
    window.__qualty_recording_enabled = true;
    window.__qualty_listeners_attached = false;
    window.__qualty_recording = true;
    
    console.log('[QUALTY RECORDER] Script loaded');
    
    // Track scroll position of last recorded action
    let lastActionScrollX = window.scrollX || window.pageXOffset || 0;
    let lastActionScrollY = window.scrollY || window.pageYOffset || 0;
    const SCROLL_THRESHOLD = 100;  // Minimum pixels difference to record scroll
    
    // Track hover state for recording hover actions
    let lastHoveredElement = null;
    let lastHoverTime = 0;
    let hoverMutationObserver = null;
    let hoverUIChanged = false;
    let elementsAddedAfterHover = [];  // Track elements that appeared after hover
    const HOVER_UI_CHANGE_DELAY = 300;  // Delay to detect UI changes after hover
    
    function getXPath(element) {
        // Prefer element's own ID
        if (element.id !== '') {
            return '//*[@id="' + element.id + '"]';
        }
        
        if (element === document.body) {
            return '/html/body';
        }
        
        // Count siblings of the same tag type
        let sameTagCount = 0;
        let position = 0;
        const siblings = element.parentNode.childNodes;
        
        for (let i = 0; i < siblings.length; i++) {
            const sibling = siblings[i];
            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                sameTagCount++;
                if (sibling === element) {
                    position = sameTagCount;
                }
            }
        }
        
        // Build XPath: only use index if there are multiple siblings of same type
        const tagName = element.tagName.toLowerCase();
        const index = sameTagCount > 1 ? '[' + position + ']' : '';
        const parentXPath = getXPath(element.parentNode);
        
        return parentXPath + '/' + tagName + index;
    }
    
    function getXPathForFill(element) {
        // For fill actions, prefer parent container with ID (more robust)
        if (element.id !== '') {
            return '//*[@id="' + element.id + '"]';
        }
        
        // Look for parent with ID (up to 3 levels up)
        let current = element.parentElement;
        let depth = 0;
        while (current && depth < 3) {
            if (current.id !== '') {
                return '//*[@id="' + current.id + '"]';
            }
            current = current.parentElement;
            depth++;
        }
        
        // Fall back to element's own XPath
        return getXPath(element);
    }
    
    function getElementDescription(element) {
        const tag = element.tagName.toLowerCase();
        const text = element.textContent?.trim().substring(0, 50) || '';
        const placeholder = element.placeholder || '';
        const label = element.labels?.[0]?.textContent || '';
        const ariaLabel = element.getAttribute('aria-label') || '';
        const id = element.id || '';
        
        if (ariaLabel) return ariaLabel;
        if (label) return label;
        if (placeholder) return placeholder;
        if (text) return text;
        if (id) return `${tag} with id "${id}"`;
        return `${tag} element`;
    }
    
    function checkAndInsertScrollAction() {
        // Get current scroll position (target coordinate)
        const currentScrollX = window.scrollX || window.pageXOffset || 0;
        const currentScrollY = window.scrollY || window.pageYOffset || 0;
        
        // Calculate scroll difference
        const deltaX = currentScrollX - lastActionScrollX;
        const deltaY = currentScrollY - lastActionScrollY;
        const absDeltaX = Math.abs(deltaX);
        const absDeltaY = Math.abs(deltaY);
        
        // Check if scroll difference exceeds threshold
        if (absDeltaX < SCROLL_THRESHOLD && absDeltaY < SCROLL_THRESHOLD) {
            return false;  // No scroll action needed
        }
        
        // Determine scroll direction based on larger delta
        let direction = 'down';
        if (absDeltaX > absDeltaY) {
            direction = deltaX > 0 ? 'right' : 'left';
        } else {
            direction = deltaY > 0 ? 'down' : 'up';
        }
        
        // Format target coordinate as "{x},{y}"
        const targetCoordinate = `${Math.round(currentScrollX)},${Math.round(currentScrollY)}`;
        
        // Create scroll action with target coordinate
        window.__qualty_actions.push({
            selector: '/html/body',
            description: `Scroll ${direction} to ${targetCoordinate}`,
            method: 'scrollto',
            arguments: [],
            target_coordinate: targetCoordinate,
            timestamp: Date.now()
        });
        
        return true;  // Scroll action was inserted
    }
    
    /**
     * Determines if a hover action should be recorded based on the clicked element.
     * 
     * Rules:
     * - Do NOT record hover if clicking the hovered element itself (e.g. "Classes" button)
     * - ONLY record hover when clicking a child of the dropdown/menu that appeared (e.g. dropdown items)
     * 
     * @param {Element} clickedElement - The element that was clicked
     * @returns {boolean} True if hover should be recorded, false otherwise
     */
    function checkAndInsertHoverAction(clickedElement) {
        // Early return if no hover context exists
        if (!lastHoveredElement || !lastHoverTime || !clickedElement) {
            return false;
        }
        
        // Never record hover when clicking the hovered element itself (e.g. parent icon/button)
        if (clickedElement === lastHoveredElement) {
            return false;
        }
        
        // Check if clicked element is inside a dropdown/collapse related to the hovered element.
        // This catches MuiCollapse, Bootstrap dropdowns, etc. even when MutationObserver misses them.
        if (isInsideDropdownMenu(clickedElement, lastHoveredElement)) {
            return recordHoverAction();
        }
        
        // Also check elementsAddedAfterHover (MutationObserver-detected UI changes)
        if (!hoverUIChanged || elementsAddedAfterHover.length === 0) {
            return false;
        }
        
        // Only record hover when clicking inside one of the newly appeared elements (dropdown children)
        for (let i = 0; i < elementsAddedAfterHover.length; i++) {
            const addedElement = elementsAddedAfterHover[i];
            if (!addedElement) continue;
            
            try {
                // Check if clicked element is the added element itself or inside it
                if (addedElement === clickedElement || 
                    (addedElement.contains && addedElement.contains(clickedElement))) {
                    // Verify clicked element is NOT the hovered element itself
                    // and that it's actually a descendant of the newly added element
                    if (clickedElement !== lastHoveredElement && 
                        isDescendantOfNewlyAdded(clickedElement, addedElement)) {
                        return recordHoverAction();
                    }
                }
            } catch (e) {
                // Element might have been removed, continue checking
                continue;
            }
        }
        
        return false;
    }
    
    /**
     * Checks if an element is a descendant of a newly added element (not the hovered element).
     * This helps distinguish between clicking the hovered element vs its dropdown children.
     * 
     * @param {Element} element - The element to check
     * @param {Element} addedElement - The newly added element (dropdown/menu)
     * @returns {boolean} True if element is a descendant of addedElement
     */
    function isDescendantOfNewlyAdded(element, addedElement) {
        if (!element || !addedElement) return false;
        if (element === addedElement) return true;
        
        // If the element is the hovered element itself, it's not a descendant of addedElement
        if (element === lastHoveredElement) {
            return false;
        }
        
        // Walk up the DOM tree to see if we reach addedElement before lastHoveredElement
        let current = element.parentElement;
        let depth = 0;
        const MAX_DEPTH = 10;
        
        while (current && depth < MAX_DEPTH) {
            if (current === addedElement) {
                return true;
            }
            // If we reach the hovered element before the added element,
            // then the clicked element is not a descendant of the added element
            if (current === lastHoveredElement) {
                return false;
            }
            current = current.parentElement;
            depth++;
        }
        
        return false;
    }
    
    /**
     * Checks if clicked element is inside a dropdown/menu structure that appeared due to hover.
     * Returns false if clicked element is the hovered element itself.
     */
    function isInsideDropdownMenu(clickedElement, hoveredElement) {
        if (!clickedElement || !hoveredElement) return false;
        
        // Don't record if clicking the hovered element itself
        if (clickedElement === hoveredElement) {
            return false;
        }
        
        // Don't record if clicked element is a descendant of the hovered element (clicking inside the trigger)
        if (hoveredElement.contains && hoveredElement.contains(clickedElement)) {
            return false;
        }
        
        let current = clickedElement.parentElement;
        let depth = 0;
        const MAX_DEPTH = 20;
        
        while (current && current !== document.body && depth < MAX_DEPTH) {
            // Stop if we've reached the hovered element (without finding a dropdown)
            if (current === hoveredElement) {
                break;
            }
            
            // Check if current element is a dropdown/menu/collapse container
            const classes = typeof current.className === 'string' ? current.className : (current.className && current.className.baseVal) || '';
            const hasDropdownClass = /dropdown|menu|popover|tooltip|collapse/i.test(classes);
            const role = current.getAttribute('role');
            const isMenu = role === 'menu' || role === 'listbox' || role === 'navigation';
            const ariaExpanded = current.getAttribute('aria-expanded');
            const isSiblingOfHovered = current.parentElement && (
                current.parentElement === hoveredElement.parentElement ||
                (hoveredElement.parentElement && current.parentElement.contains(hoveredElement))
            );
            
            if (hasDropdownClass || isMenu || ariaExpanded === 'true' || isSiblingOfHovered) {
                if (isDropdownRelatedToHovered(current, hoveredElement)) {
                    return true;
                }
            }
            
            current = current.parentElement;
            depth++;
        }
        
        return false;
    }
    
    /**
     * Checks if a dropdown element is related to the hovered element.
     * Handles: dropdown as child of hovered, hovered as child of dropdown's parent, siblings.
     */
    function isDropdownRelatedToHovered(dropdownElement, hoveredElement) {
        if (!dropdownElement || !hoveredElement) return false;
        
        // Dropdown is a descendant of hovered element (e.g. menu inside button)
        if (hoveredElement.contains && hoveredElement.contains(dropdownElement)) {
            return true;
        }
        
        // Dropdown and hovered element share a parent (siblings, e.g. MuiCollapse + icon button)
        if (dropdownElement.parentElement && dropdownElement.parentElement.contains(hoveredElement)) {
            return true;
        }
        
        // Walk up dropdown's ancestors - is hovered element an ancestor or in same branch?
        let checkParent = dropdownElement.parentElement;
        let depth = 0;
        while (checkParent && checkParent !== document.body && depth < 10) {
            if (checkParent === hoveredElement || 
                (hoveredElement.contains && hoveredElement.contains(checkParent))) {
                return true;
            }
            checkParent = checkParent.parentElement;
            depth++;
        }
        
        return false;
    }
    
    /**
     * Records the hover action and resets tracking state.
     */
    function recordHoverAction() {
        const xpath = getXPath(lastHoveredElement);
        if (!xpath) {
            return false;
        }
        
        const description = getElementDescription(lastHoveredElement);
        
        // Record hover action before the click
        window.__qualty_actions.push({
            selector: xpath,
            description: `Hover the ${description}`,
            method: 'hover',
            arguments: [],
            timestamp: lastHoverTime
        });
        
        console.log('[QUALTY RECORDER] Hover action recorded for:', description);
        
        // Reset hover tracking
        resetHoverTracking();
        
        return true;
    }
    
    /**
     * Resets all hover tracking state.
     */
    function resetHoverTracking() {
        lastHoveredElement = null;
        lastHoverTime = 0;
        hoverUIChanged = false;
        elementsAddedAfterHover = [];
        if (hoverMutationObserver) {
            hoverMutationObserver.disconnect();
            hoverMutationObserver = null;
        }
    }
    
    function startHoverTracking(element) {
        // Clean up previous observer
        if (hoverMutationObserver) {
            hoverMutationObserver.disconnect();
        }
        
        lastHoveredElement = element;
        lastHoverTime = Date.now();
        hoverUIChanged = false;
        elementsAddedAfterHover = [];
        
        // Store initial state of dropdowns/menus near the hovered element
        // Check for dropdown containers that might become visible
        const checkForDropdowns = function() {
            if (!lastHoveredElement || lastHoverTime === 0) return;
            
            // Look for dropdown containers near the hovered element (siblings or descendants)
            let current = lastHoveredElement;
            let parent = current.parentElement;
            
            // Check siblings for dropdown containers
            if (parent) {
                const siblings = Array.from(parent.children);
                for (let i = 0; i < siblings.length; i++) {
                    const sibling = siblings[i];
                    if (sibling === current) continue;
                    
                    // Check if sibling looks like a dropdown (has dropdown/dropdown-menu classes or aria attributes)
                    const classes = sibling.className || '';
                    const hasDropdownClass = /dropdown|menu|popover|tooltip|collapse/i.test(classes);
                    const ariaExpanded = sibling.getAttribute('aria-expanded');
                    const role = sibling.getAttribute('role');
                    const isMenu = role === 'menu' || role === 'listbox';
                    
                    if (hasDropdownClass || isMenu || (sibling.tagName && sibling.tagName.toLowerCase() === 'ul')) {
                        // Check if it becomes visible
                        setTimeout(function() {
                            if (sibling.offsetWidth > 0 || sibling.offsetHeight > 0 || 
                                window.getComputedStyle(sibling).display !== 'none') {
                                hoverUIChanged = true;
                                if (elementsAddedAfterHover.indexOf(sibling) === -1) {
                                    elementsAddedAfterHover.push(sibling);
                                }
                            }
                        }, 100);
                    }
                }
            }
            
            // Check for dropdowns that are descendants (already in DOM but hidden)
            const findDropdowns = function(el, depth) {
                if (depth > 3) return; // Limit depth
                if (!el || !el.children) return;
                
                const children = Array.from(el.children);
                for (let i = 0; i < children.length; i++) {
                    const child = children[i];
                    const classes = child.className || '';
                    const hasDropdownClass = /dropdown|menu|popover|tooltip|collapse/i.test(classes);
                    const role = child.getAttribute('role');
                    const isMenu = role === 'menu' || role === 'listbox';
                    
                    if (hasDropdownClass || isMenu) {
                        // Check visibility after a short delay
                        setTimeout(function() {
                            const style = window.getComputedStyle(child);
                            if (style.display !== 'none' && style.visibility !== 'hidden' && 
                                (child.offsetWidth > 0 || child.offsetHeight > 0)) {
                                hoverUIChanged = true;
                                if (elementsAddedAfterHover.indexOf(child) === -1) {
                                    elementsAddedAfterHover.push(child);
                                }
                            }
                        }, 100);
                    }
                    findDropdowns(child, depth + 1);
                }
            };
            
            findDropdowns(current, 0);
        };
        
        // Check for dropdowns after a short delay
        setTimeout(checkForDropdowns, 50);
        
        // Set up MutationObserver to detect meaningful UI changes (new elements added OR visibility changes)
        hoverMutationObserver = new MutationObserver(function(mutations) {
            // Track when new elements are added (dropdowns, menus, tooltips, etc.)
            for (let i = 0; i < mutations.length; i++) {
                const mutation = mutations[i];
                
                // Check for added nodes (new elements appearing)
                if (mutation.addedNodes.length > 0) {
                    for (let j = 0; j < mutation.addedNodes.length; j++) {
                        const node = mutation.addedNodes[j];
                        if (node.nodeType === 1) {  // Element node
                            const tagName = node.tagName ? node.tagName.toLowerCase() : '';
                            
                            // Skip script, style, meta, link tags
                            if (tagName && ['script', 'style', 'meta', 'link', 'noscript'].includes(tagName)) {
                                continue;
                            }
                            
                            // Track the element immediately
                            hoverUIChanged = true;
                            if (elementsAddedAfterHover.indexOf(node) === -1) {
                                elementsAddedAfterHover.push(node);
                            }
                        }
                    }
                }
                
                // Also check for attribute changes that might indicate visibility (aria-expanded, class changes)
                if (mutation.type === 'attributes') {
                    const target = mutation.target;
                    const attrName = mutation.attributeName;
                    
                    // Check if aria-expanded changed to true (dropdown opened)
                    if (attrName === 'aria-expanded' && target.getAttribute('aria-expanded') === 'true') {
                        // Look for dropdown container near this element
                        setTimeout(function() {
                            let dropdown = target.nextElementSibling || target.parentElement?.querySelector('[class*="dropdown"], [class*="menu"], [class*="collapse"], [role="menu"]');
                            if (dropdown && (dropdown.offsetWidth > 0 || dropdown.offsetHeight > 0)) {
                                hoverUIChanged = true;
                                if (elementsAddedAfterHover.indexOf(dropdown) === -1) {
                                    elementsAddedAfterHover.push(dropdown);
                                }
                            }
                        }, 50);
                    }
                    
                    // Check for class changes that might indicate dropdown visibility
                    if (attrName === 'class') {
                        const classes = target.className || '';
                        if (/dropdown|menu|open|show|visible|collapse|entered/i.test(classes)) {
                            setTimeout(function() {
                                const style = window.getComputedStyle(target);
                                if (style.display !== 'none' && style.visibility !== 'hidden') {
                                    hoverUIChanged = true;
                                    if (elementsAddedAfterHover.indexOf(target) === -1) {
                                        elementsAddedAfterHover.push(target);
                                    }
                                }
                            }, 50);
                        }
                    }
                }
            }
        });
        
        // Observe the document for changes - track both childList (new elements) and attributes (visibility changes)
        hoverMutationObserver.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['aria-expanded', 'class', 'style']
        });
        
        // Note: We don't record hover just because UI changed - we only record when
        // the user clicks on one of the new elements that appeared
    }
    
    /**
     * Attaches event listeners for recording user interactions.
     * This function can be safely called multiple times - it checks if listeners are already attached.
     */
    function attachEventListeners() {
        // Skip if listeners are already attached (avoid duplicates; defensive for same-document double run)
        if (window.__qualty_listeners_attached) {
            return;
        }
        
        // Capture hover events
        try {
            document.addEventListener('mouseover', function(e) {
                try {
                    if (!window.__qualty_recording || !window.__qualty_recording_enabled) return;
                    const target = e.target;
                    if (!target || target.tagName === 'HTML' || target.tagName === 'BODY') return;
                    
                    // Use nearest button/link so we track the hoverable trigger, not nested svg/span
                    const hoverTarget = target.closest('a, button, [role="button"], [role="menuitem"]') || target;
                    startHoverTracking(hoverTarget);
                } catch (err) {
                    console.error('[QUALTY RECORDER] Error in mouseover handler:', err);
                }
            }, true);
            console.log('[QUALTY RECORDER] mouseover listener attached');
        } catch (err) {
            console.error('[QUALTY RECORDER] Failed to attach mouseover listener:', err);
        }
        
        // Capture mouseout to detect when mouse leaves the hovered element
        try {
            document.addEventListener('mouseout', function(e) {
                if (!window.__qualty_recording || !window.__qualty_recording_enabled) return;
                // Only reset if mouse is leaving the last hovered element
                if (lastHoveredElement && (e.target === lastHoveredElement || lastHoveredElement.contains(e.target))) {
                    // Don't disconnect observer immediately - give it time to detect mutations
                    // The observer will be cleaned up when click happens or after timeout
                }
            }, true);
        } catch (err) {
            console.error('[QUALTY RECORDER] Failed to attach mouseout listener:', err);
        }
        
        // Capture typing (debounced); shared state for flush on click
        const TYPING_DEBOUNCE_MS = 1500;
        let typingTimeout = null;
        let lastTypingTarget = null;
        
        function recordTypingAction(inputTarget) {
            if (!inputTarget || (inputTarget.tagName !== 'INPUT' && inputTarget.tagName !== 'TEXTAREA')) return;
            try {
                checkAndInsertScrollAction();
                const xpath = getXPathForFill(inputTarget);
                if (!xpath) return;
                const description = getElementDescription(inputTarget);
                const value = inputTarget.value || '';
                window.__qualty_actions.push({
                    selector: xpath,
                    description: 'Type "' + value + '" into the ' + description,
                    method: 'fill',
                    arguments: [value],
                    timestamp: Date.now()
                });
                lastActionScrollX = window.scrollX || window.pageXOffset || 0;
                lastActionScrollY = window.scrollY || window.pageYOffset || 0;
            } catch (err) {
                console.error('[QUALTY RECORDER] Error in recordTypingAction:', err);
            }
        }
        
        function flushPendingTyping() {
            if (typingTimeout && lastTypingTarget) {
                clearTimeout(typingTimeout);
                typingTimeout = null;
                recordTypingAction(lastTypingTarget);
                lastTypingTarget = null;
            }
        }
        
        // Double-click detection: two consecutive clicks on same element within this threshold
        const DOUBLE_CLICK_MS = 400;
        let lastClickTarget = null;
        let lastClickTime = 0;
        
        // Capture clicks
        try {
            document.addEventListener('click', function(e) {
            try {
                if (!window.__qualty_recording || !window.__qualty_recording_enabled) {
                    console.log('[QUALTY RECORDER] Click ignored - recording disabled');
                    return;
                }
                const target = e.target;
                if (!target || target.tagName === 'HTML' || target.tagName === 'BODY') {
                    console.log('[QUALTY RECORDER] Click ignored - invalid target');
                    return;
                }
                
                // Flush any pending typing so it's recorded BEFORE this click (correct ordering)
                flushPendingTyping();
                
                console.log('[QUALTY RECORDER] Click detected on:', target.tagName, target.className || 'no class');
                
                // Check for hover action before click (only if UI actually changed with new elements)
                checkAndInsertHoverAction(target);
                
                // Check for scroll between this action and the previous one
                checkAndInsertScrollAction();
                
                const xpath = getXPath(target);
                if (!xpath) {
                    console.log('[QUALTY RECORDER] Click ignored - no xpath');
                    return;
                }
                
                const description = getElementDescription(target);
                const now = Date.now();
                const isDoubleClick = lastClickTarget === target && (now - lastClickTime) < DOUBLE_CLICK_MS;
                
                if (isDoubleClick) {
                    // Remove the previous single click and record a double-click instead
                    const actions = window.__qualty_actions || [];
                    if (actions.length > 0 && actions[actions.length - 1].method === 'click') {
                        actions.pop();
                    }
                    window.__qualty_actions.push({
                        selector: xpath,
                        description: `Double-click the ${description}`,
                        method: 'dblclick',
                        arguments: [],
                        timestamp: now
                    });
                    console.log('[QUALTY RECORDER] Double-click action recorded');
                    lastClickTarget = null;
                    lastClickTime = 0;
                } else {
                    const action = {
                        selector: xpath,
                        description: `Click the ${description}`,
                        method: 'click',
                        arguments: [],
                        timestamp: now
                    };
                    window.__qualty_actions.push(action);
                    console.log('[QUALTY RECORDER] Click action recorded:', action.description);
                    lastClickTarget = target;
                    lastClickTime = now;
                }
                
                // Update scroll position after recording action
                lastActionScrollX = window.scrollX || window.pageXOffset || 0;
                lastActionScrollY = window.scrollY || window.pageYOffset || 0;
                
                // Reset hover tracking after click
                resetHoverTracking();
            } catch (err) {
                console.error('[QUALTY RECORDER] Error in click handler:', err);
            }
            }, true);
            console.log('[QUALTY RECORDER] click listener attached');
        } catch (err) {
            console.error('[QUALTY RECORDER] Failed to attach click listener:', err);
        }
        
        // Capture right-clicks (contextmenu fires for right-click; click does not)
        try {
            document.addEventListener('contextmenu', function(e) {
            try {
                if (!window.__qualty_recording || !window.__qualty_recording_enabled) return;
                const target = e.target;
                if (!target || target.tagName === 'HTML' || target.tagName === 'BODY') return;
                
                flushPendingTyping();
                
                checkAndInsertScrollAction();
                
                const xpath = getXPath(target);
                if (!xpath) return;
                
                const description = getElementDescription(target);
                window.__qualty_actions.push({
                    selector: xpath,
                    description: `Right-click the ${description}`,
                    method: 'rightclick',
                    arguments: [],
                    timestamp: Date.now()
                });
                
                lastActionScrollX = window.scrollX || window.pageXOffset || 0;
                lastActionScrollY = window.scrollY || window.pageYOffset || 0;
                resetHoverTracking();
                
                console.log('[QUALTY RECORDER] Right-click action recorded');
            } catch (err) {
                console.error('[QUALTY RECORDER] Error in contextmenu handler:', err);
            }
            }, true);
            console.log('[QUALTY RECORDER] contextmenu listener attached');
        } catch (err) {
            console.error('[QUALTY RECORDER] Failed to attach contextmenu listener:', err);
        }
        
        // Capture typing (debounced)
        try {
            document.addEventListener('input', function(e) {
            try {
                if (!window.__qualty_recording || !window.__qualty_recording_enabled) return;
                const target = e.target;
                if (!target || (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA')) return;
                
                if (typingTimeout) clearTimeout(typingTimeout);
                lastTypingTarget = target;
                typingTimeout = setTimeout(function() {
                    try {
                        recordTypingAction(target);
                        typingTimeout = null;
                        lastTypingTarget = null;
                    } catch (err) {
                        console.error('[QUALTY RECORDER] Error in input timeout handler:', err);
                    }
                }, TYPING_DEBOUNCE_MS);
            } catch (err) {
                console.error('[QUALTY RECORDER] Error in input handler:', err);
            }
            }, true);
            console.log('[QUALTY RECORDER] input listener attached');
        } catch (err) {
            console.error('[QUALTY RECORDER] Failed to attach input listener:', err);
        }
        
        // Mark listeners as attached
        window.__qualty_listeners_attached = true;
        console.log('[QUALTY RECORDER] Event listeners attached');
    }
    
    // Attach event listeners. With add_init_script, this runs once per document (on every navigation).
    attachEventListeners();
    
    // Save pending actions to sessionStorage before unload (captures nav-click on same-origin navigation).
    // On the next page load (same origin), we read and merge above. Backend polling will then retrieve them.
    function flushActionsToSessionStorage() {
        try {
            var actions = (window.__qualty_actions || []).slice(0);
            if (actions.length === 0) return;
            sessionStorage.setItem(__qualty_storage_key, JSON.stringify(actions));
            console.log('[QUALTY RECORDER] Saved', actions.length, 'actions to sessionStorage before unload');
        } catch (e) {
            console.warn('[QUALTY RECORDER] Failed to save actions to sessionStorage:', e);
        }
    }
    
    window.addEventListener("pagehide", flushActionsToSessionStorage);
    window.addEventListener("beforeunload", flushActionsToSessionStorage);
})();
"""


def build_recorder_script(session_id: str) -> str:
    """Build the inject script with session_id."""
    return RECORDER_INJECT_SCRIPT_TEMPLATE.replace("__QUALTY_SESSION_ID__", session_id)
