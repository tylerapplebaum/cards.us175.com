function exportFullDataToCSV() {
    const data = window.exportInventoryData;
    
    if (!data || !Array.isArray(data) || data.length === 0) {
        alert('No data available. Please search for items first.');
        return;
    }
    
    const headers = [
        'guid', 'Year', 'Set', 'Subset', 'CardNum', 'PlayerName', 
        'Qty', 'SerialNumber', 'Authenticator', 'Grade', 'CertNumber', 
        'BoxNum', 'TxnId', 'eBayItemId', 'PurchasePrice', 
        'SalePrice', 'GradingFee', 'MktVal', 'TxnSource', 'TxnType', 
        'TxnDate'
    ];
    
    const fieldMap = {
        'guid': 'guid',
        'Year': 'Year',
        'Set': 'Set',
        'Subset': 'Subset',
        'CardNum': 'CardNum',
        'PlayerName': 'PlayerName',
        'Qty': 'Qty',
        'SerialNumber': 'SerialNumber',
        'Authenticator': 'Authenticator',
        'Grade': 'Grade',
        'CertNumber': 'CertNumber',
        'BoxNum': 'BoxNum',
        'TxnId': 'TxnId',
        'eBayItemId': 'eBayItemId',
        'PurchasePrice': 'PurchasePrice',
        'SalePrice': 'SalePrice',
        'GradingFee': 'GradingFee',
        'MktVal': 'MktVal',
        'TxnSource': 'TxnSource',
        'TxnType': 'TxnType',
        'TxnDate': 'TxnDate'
    };
    
    // Generate CSV content
    let csvContent = headers.join(',') + '\n';
    
    data.forEach(item => {
        const row = headers.map(header => {
            const fieldName = fieldMap[header];
            const value = item[fieldName] || '';
            const escaped = value.toString().replace(/"/g, '""');
            return /[",\n]/.test(escaped) ? `"${escaped}"` : escaped;
        });
        csvContent += row.join(',') + '\n';
    });
    
    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `inventory_export_${new Date().getTime()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    alert(`Export complete! ${data.length} rows exported.`);
}
