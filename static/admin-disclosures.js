(() => {
  const panels = [...document.querySelectorAll('.admin-page .admin-panel')];
  panels.forEach((panel) => {
    const heading = [...panel.children].find((child) => child.classList.contains('panel-heading'));
    if (!heading) return;

    const details = document.createElement('details');
    details.className = 'admin-panel-disclosure';
    const summary = document.createElement('summary');
    summary.className = 'admin-panel-summary';
    summary.append(heading);

    const content = document.createElement('div');
    content.className = 'admin-panel-body';
    [...panel.childNodes].forEach((node) => {
      if (node !== summary && node !== heading) content.append(node);
    });
    details.append(summary, content);
    panel.append(details);
  });

  const openHashPanel = () => {
    if (!location.hash) return;
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    const disclosure = target?.querySelector(':scope > .admin-panel-disclosure');
    if (disclosure) disclosure.open = true;
  };
  document.querySelectorAll('.admin-tabs a[href^="#"]').forEach((link) => {
    link.addEventListener('click', () => {
      const target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
      const disclosure = target?.querySelector(':scope > .admin-panel-disclosure');
      if (disclosure) disclosure.open = true;
    });
  });
  window.addEventListener('hashchange', openHashPanel);
  openHashPanel();
})();
