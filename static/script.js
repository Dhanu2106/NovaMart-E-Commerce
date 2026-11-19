
function searchProducts() {
    let input = document.getElementById("searchInput")
        .value.toLowerCase();

    let products = document.querySelectorAll(".product-card");
    let count = 0;

    products.forEach(function(product) {
        let name = product.querySelector("h3")
            .textContent.toLowerCase();

        if (name.includes(input)) {
            product.style.display = "block";
            count++;
        } else {
            product.style.display = "none";
        }
    });

    document.getElementById("noResults").style.display =
        count === 0 ? "block" : "none";
}

function addToCart(productName) {
    alert(productName + " - Cart feature will be available soon!");
}
