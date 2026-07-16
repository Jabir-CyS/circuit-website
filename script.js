/* ============================================================
   Circuit — Shared behavior (header, mobile menu, newsletter)
   Included on every page.
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  // Mobile menu toggle
  const navToggle = document.querySelector('.nav-toggle');
  const mobileNav = document.querySelector('.mobile-nav');
  const navOverlay = document.querySelector('.nav-overlay');
  const body = document.body;

  if (navToggle && mobileNav && navOverlay) {
    function openMenu(){
      navToggle.classList.add('open');
      navToggle.setAttribute('aria-expanded', 'true');
      mobileNav.classList.add('open');
      navOverlay.classList.add('open');
      body.classList.add('menu-open');
    }
    function closeMenu(){
      navToggle.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
      mobileNav.classList.remove('open');
      navOverlay.classList.remove('open');
      body.classList.remove('menu-open');
    }
    navToggle.addEventListener('click', () => {
      mobileNav.classList.contains('open') ? closeMenu() : openMenu();
    });
    navOverlay.addEventListener('click', closeMenu);
    document.querySelectorAll('.mobile-nav a').forEach(a => a.addEventListener('click', closeMenu));
    document.addEventListener('keydown', (e) => { if(e.key === 'Escape') closeMenu(); });
    window.addEventListener('resize', () => { if(window.innerWidth > 860) closeMenu(); });
  }

  // Newsletter form
  // If the form's "action" still points to the placeholder Formspree URL,
  // we just show a demo confirmation locally. Once you swap in your real
  // Formspree form ID (see deployment notes), this will actually submit
  // the email via fetch and show the same confirmation.
  const form = document.getElementById('newsletterForm');
  const msg = document.getElementById('signupMsg');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const isConfigured = form.action && !form.action.includes('YOUR_FORM_ID');

      if (!isConfigured) {
        if (msg) msg.classList.add('show');
        form.reset();
        return;
      }

      try {
        const res = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          headers: { Accept: 'application/json' }
        });
        if (res.ok) {
          if (msg) msg.classList.add('show');
          form.reset();
        } else {
          alert('Something went wrong — please try again.');
        }
      } catch (err) {
        alert('Something went wrong — please check your connection and try again.');
      }
    });
  }
});
