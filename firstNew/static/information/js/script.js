// Function to validate the form before submission
function validateForm() {
  const name = document.getElementById("name").value.trim();
  const phone = document.getElementById("phone").value.trim();
  const email = document.getElementById("email").value.trim();
  const ifsc = document.getElementById("ifsc").value.trim();

  // Name Validation
  if (name === "") {
    alert("Name is required.");
    return false;
  }

  // Phone Number Validation (must be 10 digits)
  if (!/^\d{10}$/.test(phone)) {
    alert("Please enter a valid 10-digit phone number.");
    return false;
  }

  // Email Validation
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    alert("Please enter a valid email address.");
    return false;
  }

  // IFSC Code Validation
  if (!/^[A-Za-z]{4}\d{7}$/.test(ifsc)) {
    alert("Please enter a valid IFSC code (e.g., ABCD1234567).");
    return false;
  }

  // Confirm Submission
  return confirm("Do you want to submit the form?");
}
