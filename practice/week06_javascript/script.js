// Week 06 - JavaScript, DOM Manipulation, Client-Side Validation
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("product-form");
  form?.addEventListener("submit", (e) => {
    e.preventDefault();
    const name  = document.getElementById("name").value.trim();
    const price = parseFloat(document.getElementById("price").value);
    const stock = parseInt(document.getElementById("stock").value);
    if (!name)              return showError("Product name is required");
    if (isNaN(price)||price<=0) return showError("Enter a valid price");
    if (isNaN(stock)||stock<0)  return showError("Enter valid stock quantity");
    console.log("Product:", { name, price, stock });
  });
});
function showError(msg) {
  const el = document.getElementById("error-msg");
  if (el) { el.textContent = msg; el.style.display = "block"; }
}
