# Third-party notices

## PyJanggi

This project vendors the game-rule code in `third_party/pyjanggi`, derived from [sungho-cho/pyjanggi](https://github.com/sungho-cho/pyjanggi) at commit `5ee1b28e47db6038b90e250201256c112d259b00`.

Copyright (c) 2022 Sungho Cho. Licensed under the MIT License. The original license text is retained in `third_party/pyjanggi/LICENSE`.

Local adaptations remove the pygame UI and NumPy dependency and correct the palace column boundary check used by the learning application.

## Kakao-style Janggi piece images

The 14 SVG piece images in `public/pieces/kakao-*.svg` are from [Kadagaden/chess-pieces](https://github.com/Kadagaden/chess-pieces/tree/master/janggi_kakao_janggi_style_white), by Kadagaden. They are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); the supplied license text is retained in `public/pieces/Kadagaden-chess-pieces-LICENSE.txt`.

## Fairy-Stockfish WebAssembly engine

`public/engine/` contains Fairy-Stockfish NNUE WebAssembly package version 1.1.12 from [fairy-stockfish/Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish). Fairy-Stockfish is licensed under GPL-3.0-or-later; its license text is retained in `public/engine/COPYING.txt`. This application distributes the engine as part of the browser client and is therefore released under GPL-3.0-or-later; the source is available from the project's GitHub repository.
