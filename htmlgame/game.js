let money = 100;
let factories = 0;
const factoryCost = 50;

const moneyEl = document.getElementById('money');
const factoriesEl = document.getElementById('factories');
const buildBtn = document.getElementById('buildBtn');
const container = document.getElementById('factoriesContainer');

function updateUI() {
  moneyEl.textContent = money;
  factoriesEl.textContent = factories;
  buildBtn.disabled = money < factoryCost;
}

buildBtn.addEventListener('click', () => {
  if (money >= factoryCost) {
    money -= factoryCost;
    factories++;
    const factory = document.createElement('div');
    factory.className = 'factory';
    container.appendChild(factory);
    updateUI();
  }
});

// Пассивный доход: каждый завод приносит $1 каждые 3 секунды
setInterval(() => {
  if (factories > 0) {
    money += factories;
    updateUI();
  }
}, 3000);

updateUI();