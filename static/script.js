document.addEventListener('DOMContentLoaded', () => {
  const forms = document.querySelectorAll('form');
  forms.forEach((form) => {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      form.addEventListener('submit', () => {
        submitButton.disabled = true;
        submitButton.textContent = 'Saving...';
      });
    }
  });

  const purchaseForm = document.getElementById('purchaseForm');
  const weightInput = document.getElementById('weight');
  const rateInput = document.getElementById('rate');
  const totalInput = document.getElementById('total');

  if (purchaseForm && weightInput && rateInput && totalInput) {
    const formatPKR = (value) => value.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

    const recalcTotal = () => {
      const weight = parseFloat(weightInput.value) || 0;
      const rate = parseFloat(rateInput.value) || 0;
      totalInput.value = formatPKR(weight * rate);
    };

    weightInput.addEventListener('input', recalcTotal);
    rateInput.addEventListener('input', recalcTotal);
    recalcTotal();
  }

  const navToggle = document.getElementById('navToggle');
  const navDrawer = document.getElementById('navDrawer');
  if (navToggle && navDrawer) {
    navToggle.addEventListener('click', () => {
      navDrawer.classList.toggle('open');
    });
  }

  const toggleButton = document.getElementById('toggleBtn');
  const passwordInput = document.getElementById('password');
  const eyeIcon = document.getElementById('eyeIcon');

  if (toggleButton && passwordInput && eyeIcon) {
    toggleButton.addEventListener('click', () => {
      const isHidden = passwordInput.type === 'password';
      passwordInput.type = isHidden ? 'text' : 'password';
      toggleButton.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
      eyeIcon.innerHTML = isHidden
        ? '<path d="M3 3l18 18"></path><path d="M10.58 10.58A3 3 0 0 0 13.42 13.42"></path><path d="M9.88 4.18A10.6 10.6 0 0 1 12 4c7 0 11 8 11 8a20.9 20.9 0 0 1-4.12 5.18"></path><path d="M6.61 6.61A19.8 19.8 0 0 0 1 12s4 8 11 8a10.6 10.6 0 0 0 4.12-1.18"></path>'
        : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
    });
  }

  const productSelect = document.querySelector('select[name="product"]');
  const stockDisplay = document.getElementById('stock-display');

  if (productSelect && stockDisplay) {
    const updateStock = () => {
      const selectedProduct = encodeURIComponent(productSelect.value);
      if (!selectedProduct) {
        stockDisplay.textContent = 'Available Stock: Select a product to calculate';
        return;
      }

      fetch(`/stock/${selectedProduct}`)
        .then((response) => response.json())
        .then((data) => {
          stockDisplay.textContent = `Available Stock: ${data.available_stock}`;
        })
        .catch(() => {
          stockDisplay.textContent = 'Available Stock: unavailable';
        });
    };

    productSelect.addEventListener('change', updateStock);
    updateStock();
  }
});
