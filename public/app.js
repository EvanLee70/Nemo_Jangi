const boardElement = document.querySelector('#board');
const statusElement = document.querySelector('#status');
const recommendationsElement = document.querySelector('#recommendations');
const historyElement = document.querySelector('#history');
const passButton = document.querySelector('#pass-turn');
const svgNamespace = 'http://www.w3.org/2000/svg';
const pieceAssetNames = { 장: 'king', 사: 'advisor', 마: 'horse', 상: 'elephant', 차: 'chariot', 포: 'cannon', 졸: 'pawn' };
let state;
let selected = null;

async function request(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || '요청을 처리하지 못했습니다.');
  return payload;
}

function key(square) { return square.join(','); }
function moveKey(from, to) { return `${key(from)}>${key(to)}`; }

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(svgNamespace, name);
  Object.entries(attributes).forEach(([attribute, value]) => element.setAttribute(attribute, value));
  return element;
}

function createBoardLines() {
  const overlay = svgElement('svg', { class: 'board-lines', viewBox: '0 0 9 10', preserveAspectRatio: 'none', 'aria-hidden': 'true' });
  const grid = svgElement('g', { class: 'grid-lines' });
  for (let column = 0.5; column <= 8.5; column += 1) grid.append(svgElement('line', { x1: column, y1: 0.5, x2: column, y2: 9.5 }));
  for (let row = 0.5; row <= 9.5; row += 1) grid.append(svgElement('line', { x1: 0.5, y1: row, x2: 8.5, y2: row }));
  overlay.append(grid);
  const palaces = svgElement('g', { class: 'palace-lines' });
  [0.5, 7.5].forEach(top => {
    palaces.append(svgElement('line', { x1: 3.5, y1: top, x2: 5.5, y2: top + 2 }));
    palaces.append(svgElement('line', { x1: 5.5, y1: top, x2: 3.5, y2: top + 2 }));
  });
  overlay.append(palaces);
  return overlay;
}

function showMoveGuides(origin) {
  const overlay = boardElement.querySelector('.board-lines');
  overlay.querySelector('.move-guides')?.remove();
  const guides = svgElement('g', { class: 'move-guides' });
  state.legalMoves.filter(move => key(move.from) === key(origin)).forEach(move => {
    guides.append(svgElement('line', { x1: origin[1] + 0.5, y1: origin[0] + 0.5, x2: move.to[1] + 0.5, y2: move.to[0] + 0.5 }));
    guides.append(svgElement('circle', { cx: move.to[1] + 0.5, cy: move.to[0] + 0.5, r: '.10' }));
    boardElement.querySelectorAll('.square').forEach(square => {
      if (square.dataset.square === key(move.to)) square.classList.add('is-destination');
    });
  });
  overlay.append(guides);
}

function render(nextState) {
  state = nextState;
  selected = null;
  const legal = new Set(state.legalMoves.map(move => moveKey(move.from, move.to)));
  const origins = new Set(state.legalMoves.map(move => key(move.from)));
  boardElement.replaceChildren(createBoardLines());
  state.board.forEach((row, rowIndex) => row.forEach((piece, columnIndex) => {
    const square = document.createElement('button');
    square.className = `square ${piece ? piece.side : ''}`;
    square.setAttribute('aria-label', piece ? `${piece.side} ${piece.type}` : '빈 칸');
    square.dataset.square = `${rowIndex},${columnIndex}`;
    if (piece) {
      const pieceImage = document.createElement('img');
      pieceImage.className = 'piece-image';
      pieceImage.src = `/pieces/kakao-${piece.side === 'cho' ? 'blue' : 'red'}-${pieceAssetNames[piece.type]}.svg`;
      pieceImage.alt = `${piece.side === 'cho' ? '초' : '한'} ${piece.type}`;
      square.append(pieceImage);
    }
    if (origins.has(`${rowIndex},${columnIndex}`)) square.classList.add('can-move');
    square.addEventListener('click', () => chooseSquare([rowIndex, columnIndex], legal));
    boardElement.append(square);
  }));
  const isHumanTurn = state.turn === state.humanSide && !state.gameOver;
  statusElement.textContent = state.gameOver ? '대국이 끝났습니다.' : state.inCheck ? '장군입니다. 궁을 지키는 수를 두어야 합니다.' : isHumanTurn ? '내 말을 선택하면 이동 경로가 투명선으로 표시됩니다.' : '컴퓨터가 생각하고 있습니다.';
  passButton.disabled = !state.canPass;
  document.querySelector('#cho-score').textContent = state.scores.cho;
  document.querySelector('#han-score').textContent = state.scores.han;
  document.querySelector('#recommendation-count').textContent = `(${state.recommendations.length})`;
  recommendationsElement.replaceChildren(...state.recommendations.map((move, index) => {
    const item = document.createElement('li'); item.className = 'recommendation';
    item.innerHTML = `<strong>${index + 1}. ${move.notation}</strong><small>${move.reason}</small>`;
    item.addEventListener('click', () => play(move.from, move.to));
    return item;
  }));
  historyElement.replaceChildren(...state.moveHistory.map(move => {
    const item = document.createElement('li');
    item.textContent = move.pass ? `${move.side === 'cho' ? '초' : '한'} 한 수 쉼` : `${move.side === 'cho' ? '초' : '한'} ${move.from[0] + 1}${move.from[1] + 1} → ${move.to[0] + 1}${move.to[1] + 1}`;
    return item;
  }));
}

function chooseSquare(square, legal) {
  if (state.turn !== state.humanSide || state.gameOver) return;
  if (!selected) {
    if (state.legalMoves.some(move => key(move.from) === key(square))) {
      selected = square;
      document.querySelector(`[data-square="${key(square)}"]`).classList.add('selected');
      showMoveGuides(square);
    }
    return;
  }
  if (legal.has(moveKey(selected, square))) play(selected, square);
  else render(state);
}

async function play(from, to) {
  try { render(await request('/api/move', { method: 'POST', body: JSON.stringify({ from, to }) })); }
  catch (error) { statusElement.textContent = error.message; }
}

document.querySelector('#new-game').addEventListener('click', async () => {
  try {
    render(await request('/api/new', { method: 'POST', body: JSON.stringify({ level: Number(document.querySelector('#level').value), humanSide: document.querySelector('#side').value }) }));
  } catch (error) { statusElement.textContent = error.message; }
});
passButton.addEventListener('click', async () => {
  try { render(await request('/api/pass', { method: 'POST', body: '{}' })); }
  catch (error) { statusElement.textContent = error.message; }
});
request('/api/state').then(render).catch(error => { statusElement.textContent = error.message; });