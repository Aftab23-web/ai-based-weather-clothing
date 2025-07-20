const togglePassword = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("password");
  const eyeIcon = document.getElementById("eyeIcon");

  togglePassword.addEventListener("click", function () {
    const isPassword = passwordInput.type === "password";
    passwordInput.type = isPassword ? "text" : "password";

    // Replace SVG for eye/eye-off
    eyeIcon.outerHTML = isPassword
      ? `<svg id="eyeIcon" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none"
               viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
           <path stroke-linecap="round" stroke-linejoin="round"
                 d="M15 12a3 3 0 11-6 0 3 3 0 016 0zm-9 0a9 9 0 0118 0 9 9 0 01-18 0z" />
         </svg>`
      : `<svg id="eyeIcon" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none"
               viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
           <path stroke-linecap="round" stroke-linejoin="round"
                 d="M13.875 18.825A10.05 10.05 0 0112 19C6.477 19 2 14.523 2 9.998 2 8.98 2.152 7.997 2.438 7.069m4.136 4.13A3 3 0 0012 15a3 3 0 002.121-.879m1.76-1.76a3 3 0 00.879-2.121 3 3 0 00-.879-2.121M15 9h.01M2.458 12C3.732 7.943 7.522 5 12 5c1.682 0 3.265.42 4.625 1.158" />
         </svg>`;
  });

async function getRecommendation() {
  const city = document.getElementById('city').value.trim();

  if (!city) {
    alert("Please enter a city");
    return;
  }
fetch("/recommend", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ city, preference })
})
.then(res => res.json())
.then(data => {
  if (data.redirect) {
    window.location.href = data.redirect;
  } else if (data.error) {
    alert(data.error);  // You can use a better styled popup/toast instead
  }
})
.catch(() => alert(" Something went wrong. Please try again."));
}

