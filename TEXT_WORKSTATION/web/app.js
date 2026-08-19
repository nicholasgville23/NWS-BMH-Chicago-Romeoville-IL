// Simple web preview script to load config.json (may require a local server)
fetch('../config.json')
  .then(r => r.json())
  .then(cfg => {
    document.getElementById('ip').textContent = `IP: ${cfg.ip_address}:${cfg.port}  (${cfg.network_status})`;
    document.getElementById('send').addEventListener('click', () => {
      alert('Send stub - message:\n' + document.getElementById('msg').value);
    });
  })
  .catch(err => console.error('Failed to load config.json', err));
