// Microinteraction utilities: nav highlighting, reveal-on-scroll, ripple effect, smooth anchors
(function(){
  'use strict';
  document.addEventListener('DOMContentLoaded', function(){
    try{
      // Highlight active nav link
      var path = location.pathname.replace(/\/$/, '');
      document.querySelectorAll('.nav-link').forEach(function(a){
        var href = a.getAttribute('href') || '';
        if(href.replace(/\/$/, '') === path){ a.classList.add('active'); }
      });

      // Reveal on scroll
      var io = new IntersectionObserver(function(entries){
        entries.forEach(function(e){
          if(e.isIntersecting){
            e.target.classList.add('visible');
            io.unobserve(e.target);
          }
        });
      }, { threshold: 0.12 });
      document.querySelectorAll('.reveal').forEach(function(el){ io.observe(el); });

      // Ripple effect on buttons
      document.querySelectorAll('button.btn, a.btn').forEach(function(btn){
        btn.addEventListener('click', function(ev){
          var rect = this.getBoundingClientRect();
          var ripple = document.createElement('span');
          ripple.className = 'ripple';
          var size = Math.max(rect.width, rect.height);
          ripple.style.width = ripple.style.height = size + 'px';
          ripple.style.left = (ev.clientX - rect.left - size/2) + 'px';
          ripple.style.top = (ev.clientY - rect.top - size/2) + 'px';
          this.appendChild(ripple);
          setTimeout(function(){ ripple.remove(); }, 650);
        });
      });

      // Smooth scroll for anchors
      document.querySelectorAll('a[href^="#"]').forEach(function(a){
        a.addEventListener('click', function(e){
          var hash = this.getAttribute('href');
          if(hash.length>1){
            var target = document.querySelector(hash);
            if(target){ e.preventDefault(); target.scrollIntoView({behavior:'smooth', block:'center'}); }
          }
        });
      });

      // Floating back button behavior
      var backBtn = document.getElementById('floating-back');
      try{
        if(backBtn){
          // Hide on dashboard/root
          var hidePaths = ['/ui/dashboard','/','/ui/'];
          if(hidePaths.indexOf(location.pathname.replace(/\/$/, '')) !== -1){ backBtn.style.display = 'none'; }
          backBtn.addEventListener('click', function(e){
            e.preventDefault();
            if(window.history.length>1){ window.history.back(); }
            else { window.location.href = '/ui/dashboard'; }
          });
        }
      }catch(be){ console.error('backBtn error', be); }

      // Hide duplicate or stray 'Cargar' buttons (sometimes injected or rotated)
      try{
        document.querySelectorAll('button').forEach(function(b){
          if(b.id !== 'btn-load-cancha' && b.textContent && b.textContent.trim()==='Cargar'){
            b.style.display = 'none';
            // also ensure it's not focusable
            b.setAttribute('aria-hidden','true');
            b.tabIndex = -1;
          }
        });
      }catch(e){ /* ignore */ }

    }catch(err){ console.error('ui.js init error', err); }
  });
})();
