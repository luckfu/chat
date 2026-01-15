console.log("Custom script loaded!");

// 注入自定义 CSS
function injectCustomStyles() {
  const styleId = 'chainlit-custom-styles';
  // 如果已存在，先移除旧的以便更新
  const oldStyle = document.getElementById(styleId);
  if (oldStyle) oldStyle.remove();

  const css = `
        /* 
           ===== 侧边栏宽度调整 =====
           只调整 Drawer 本身的宽度，不强制固定容器宽度，
           以免在侧边栏收起时导致页面左侧留出空白区域。
        */
        [class*="MuiDrawer-paper"] {
            width: 350px !important;
            max-width: 350px !important;
            /* 背景色微调，使其在 Overlay 模式下更明显 */
            background-color: #1a1b26 !important; 
        }
        
        /* 
           移除之前对 #root 容器的强制宽度限制 
           这样侧边栏收起时，容器可以正常缩小，不会导致按钮悬浮
        */

        /* 恢复新建按钮显示 */
        #new-chat-button {
            display: flex !important;
            opacity: 1 !important;
            visibility: visible !important;
        }
        
        /* 仅隐藏这两个确实不需要的元素 */
        #theme-toggle, .watermark {
            display: none !important;
        }
    `;

  const style = document.createElement('style');
  style.id = styleId;
  style.textContent = css;
  document.head.appendChild(style);
  console.log("Custom CSS injected successfully (v2)");
}

// 立即执行注入
injectCustomStyles();

// ===== 自动展开 Thinking 步骤 =====
const alreadyExpanded = new WeakSet();

function autoOpenSteps(element) {
  if (element.matches?.('button[id^="step-"]')) {
    tryExpand(element);
  }
  element.querySelectorAll?.('button[id^="step-"]').forEach((btn) => {
    tryExpand(btn);
  });
}

function tryExpand(btn) {
  const isClosed = btn.getAttribute('data-state') === 'closed';
  if (isClosed && !alreadyExpanded.has(btn) && btn.querySelector('svg.lucide-chevron-down')) {
    btn.click();
    alreadyExpanded.add(btn);
  }
}

// 观察 DOM 变化
const mutationObserver = new MutationObserver((mutationList) => {
  for (const mutation of mutationList) {
    if (mutation.type === 'childList') {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === Node.ELEMENT_NODE) {
          autoOpenSteps(node);
          // 确保 CSS 始终存在
          if (!document.getElementById('chainlit-custom-styles')) {
            injectCustomStyles();
          }
        }
      }
    }
  }
});

mutationObserver.observe(document.body, {
  childList: true,
  subtree: true,
});

// 初始运行
document.querySelectorAll('button[id^="step-"]').forEach(autoOpenSteps);
