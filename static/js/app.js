document.addEventListener('DOMContentLoaded', () => {
    const addAssetForm = document.getElementById('add-asset-form');
    const assetsTableBody = document.getElementById('assets-table-body');
    const noAssetsMessage = document.getElementById('no-assets-message');
    const messageBox = document.getElementById('message-box');

    const totalCurrentValueSpan = document.getElementById('total-current-value');
    const totalBuyingValueSpan = document.getElementById('total-buying-value');
    const overallProfitLossUsdSpan = document.getElementById('overall-profit-loss-usd');
    const overallProfitLossPercentageSpan = document.getElementById('overall-profit-loss-percentage');

    // Function to display messages (errors/success)
    function showMessage(message, type = 'success') {
        messageBox.textContent = message;
        messageBox.classList.remove('hidden', 'bg-red-100', 'text-red-700', 'bg-green-100', 'text-green-700');
        if (type === 'success') {
            messageBox.classList.add('bg-green-100', 'text-green-700');
        } else {
            messageBox.classList.add('bg-red-100', 'text-red-700');
        }
        setTimeout(() => {
            messageBox.classList.add('hidden');
        }, 5000); // Hide after 5 seconds
    }

    // Function to fetch assets from the backend API
    async function fetchAssets() {
        try {
            const response = await fetch('/api/assets');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            renderAssets(data.assets);
            renderOverallSummary(data);
        } catch (error) {
            console.error('Error fetching assets:', error);
            showMessage('Failed to load assets. Please try again later.', 'error');
            assetsTableBody.innerHTML = ''; // Clear table on error
            noAssetsMessage.classList.remove('hidden'); // Show no assets message
        }
    }

    // Function to render assets in the table
    function renderAssets(assets) {
        assetsTableBody.innerHTML = ''; // Clear existing rows
        if (assets.length === 0) {
            noAssetsMessage.classList.remove('hidden');
            return;
        } else {
            noAssetsMessage.classList.add('hidden');
        }

        assets.forEach(asset => {
            const row = document.createElement('tr');

            // Determine class for profit/loss percentage styling
            let profitLossClass = '';
            // Strip '%' and convert to number for comparison
            const percentageValue = parseFloat(asset.profit_loss_percentage.replace('%', ''));
            if (percentageValue > 0) {
                profitLossClass = 'profit';
            } else if (percentageValue < 0) {
                profitLossClass = 'loss';
            } else {
                profitLossClass = 'even'; // For 0% profit/loss
            }

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 capitalize">${asset.name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${asset.quantity}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${asset.buying_price_per_unit}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${asset.current_price_per_unit}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${asset.buying_value_usd}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${asset.current_value_usd}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 ${profitLossClass}">${asset.profit_loss_usd}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 ${profitLossClass}">${asset.profit_loss_percentage}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button data-id="${asset.id}" class="delete-btn text-red-600 hover:text-red-900 transition-colors duration-300 rounded-md p-2">Delete</button>
                </td>
            `;
            assetsTableBody.appendChild(row);
        });

        // Attach event listeners to delete buttons
        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', handleDelete);
        });
    }

    // Function to render overall portfolio summary
    function renderOverallSummary(data) {
        totalCurrentValueSpan.textContent = data.total_portfolio_current_value;
        totalBuyingValueSpan.textContent = data.total_portfolio_buying_value;
        overallProfitLossUsdSpan.textContent = data.overall_profit_loss_usd;
        overallProfitLossPercentageSpan.textContent = data.overall_profit_loss_percentage;

        // Apply color based on overall profit/loss
        const overallPercentageValue = parseFloat(data.overall_profit_loss_percentage.replace('%', ''));
        const elementsToColor = [overallProfitLossUsdSpan, overallProfitLossPercentageSpan];
        elementsToColor.forEach(el => {
            el.classList.remove('profit', 'loss', 'even');
            if (overallPercentageValue > 0) {
                el.classList.add('profit');
            } else if (overallPercentageValue < 0) {
                el.classList.add('loss');
            } else {
                el.classList.add('even');
            }
        });
    }


    // Handle form submission for adding assets
    addAssetForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Prevent default form submission

        const formData = new FormData(addAssetForm);
        const assetData = {};
        formData.forEach((value, key) => {
            assetData[key] = value;
        });

        try {
            const response = await fetch('/api/assets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(assetData)
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(result.message, 'success');
                addAssetForm.reset(); // Clear the form
                fetchAssets(); // Refresh asset list
            } else {
                showMessage(`Error: ${result.error || 'Failed to add asset.'}`, 'error');
            }
        } catch (error) {
            console.error('Error adding asset:', error);
            showMessage('Failed to add asset due to a network error.', 'error');
        }
    });

    // Handle delete button click
    async function handleDelete(e) {
        const assetId = e.target.dataset.id;
        if (!confirm('Are you sure you want to delete this asset?')) { // Using confirm for simplicity, replace with custom modal in production
            return;
        }

        try {
            const response = await fetch(`/api/assets/${assetId}`, {
                method: 'DELETE'
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(result.message, 'success');
                fetchAssets(); // Refresh asset list
            } else {
                showMessage(`Error: ${result.error || 'Failed to delete asset.'}`, 'error');
            }
        } catch (error) {
            console.error('Error deleting asset:', error);
            showMessage('Failed to delete asset due to a network error.', 'error');
        }
    }

    // Initial fetch of assets when the page loads
    fetchAssets();
});
