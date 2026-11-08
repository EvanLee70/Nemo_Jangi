class FairyStockfishEngine {
  constructor() {
    this.instance = null;
    this.readyPromise = null;
    this.listeners = new Set();
    this.searching = false;
  }

  async init() {
    if (this.readyPromise) return this.readyPromise;
    this.readyPromise = this.load();
    return this.readyPromise;
  }

  async load() {
    if (!self.crossOriginIsolated || typeof SharedArrayBuffer === 'undefined') {
      throw new Error('이 브라우저는 장기 엔진에 필요한 격리 기능을 지원하지 않습니다.');
    }
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = '/engine/stockfish.js';
      script.onload = resolve;
      script.onerror = () => reject(new Error('장기 엔진 파일을 불러오지 못했습니다.'));
      document.head.append(script);
    });
    if (!self.Stockfish) throw new Error('장기 엔진을 시작하지 못했습니다.');
    this.instance = await self.Stockfish();
    this.instance.addMessageListener(line => this.listeners.forEach(listener => listener(line)));
    await this.request('uci', line => line === 'uciok');
    await this.request('setoption name UCI_Variant value janggicasual', () => false, false);
    await this.request('isready', line => line === 'readyok');
  }

  request(command, complete, wait = true) {
    if (!wait) {
      this.instance.postMessage(command);
      return Promise.resolve();
    }
    return new Promise(resolve => {
      const listener = line => {
        if (!complete(line)) return;
        this.listeners.delete(listener);
        resolve();
      };
      this.listeners.add(listener);
      this.instance.postMessage(command);
    });
  }

  async chooseMove(fen, milliseconds) {
    await this.init();
    if (this.searching) throw new Error('컴퓨터가 이미 수를 계산하고 있습니다.');
    this.searching = true;
    try {
      this.instance.postMessage(`position fen ${fen}`);
      return await new Promise((resolve, reject) => {
        const listener = line => {
          if (!line.startsWith('bestmove ')) return;
          this.listeners.delete(listener);
          const move = line.split(/\s+/)[1];
          if (!move || move === '(none)') reject(new Error('엔진이 둘 수 있는 수를 찾지 못했습니다.'));
          else resolve(move);
        };
        this.listeners.add(listener);
        this.instance.postMessage(`go movetime ${milliseconds}`);
      });
    } finally {
      this.searching = false;
    }
  }
}

const janggiEngine = new FairyStockfishEngine();
