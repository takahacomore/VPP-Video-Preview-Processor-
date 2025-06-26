window.onload = function () {
    const csInterface = new CSInterface();
    const searchButton = document.getElementById('search-button');
    const searchInput = document.getElementById('search-input');
    const resultsContainer = document.getElementById('results-container');
    const modeImageBtn = document.getElementById('mode-image');
    const modeTextBtn = document.getElementById('mode-text');
    const apiBaseUrl = 'http://127.0.0.1:5000';

    let displayMode = 'all';
    let lastQuery = '';

    function setActiveMode(mode) {
        displayMode = mode;
        modeImageBtn.classList.toggle('active', mode === 'image');
        modeTextBtn.classList.toggle('active', mode === 'text');
    }

    modeImageBtn.addEventListener('click', function() {
        setActiveMode('image');
        performSearch();
    });
    modeTextBtn.addEventListener('click', function() {
        setActiveMode('text');
        performSearch();
    });

    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            performSearch();
        }
    });

    function performSearch() {
        const query = searchInput.value;
        lastQuery = query;
        if (!query) {
            resultsContainer.innerHTML = '<p>Введите поисковый запрос.</p>';
            return;
        }

        resultsContainer.innerHTML = '<p>Идет поиск...</p>';

        fetch(`${apiBaseUrl}/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                displayResults(data, query);
            })
            .catch(error => {
                console.error('Error fetching search results:', error);
                resultsContainer.innerHTML = `<p>Ошибка при подключении к API. Убедитесь, что сервер api_server.py запущен.</p><p style="font-size: 0.8em; color: #888;">${error}</p>`;
            });
    }

    function highlightText(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<span class="highlight">$1</span>');
    }

    function formatSize(bytes) {
        if (!bytes || isNaN(bytes)) return '';
        if (bytes < 1024) return bytes + ' Б';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' КБ';
        return (bytes / (1024 * 1024)).toFixed(1) + ' МБ';
    }

    async function getImageSize(url) {
        // Пробуем получить размер файла через HEAD-запрос
        try {
            const response = await fetch(url, { method: 'HEAD' });
            const size = response.headers.get('Content-Length');
            return size ? formatSize(parseInt(size)) : '';
        } catch {
            return '';
        }
    }

    function importMediaWithInOut(filePath, inTimecode, outTimecode, fps) {
        csInterface.evalScript(
            `importMediaWithInOut('${filePath.replace(/\\/g, '/')}', '${inTimecode}', '${outTimecode}', '${fps}')`,
            (result) => {
                if (result.startsWith("Error:")) {
                } else {
                    console.log(result);
                }
            }
        );
    }

    async function displayResults(results, query) {
        // alert(JSON.stringify(results, null, 2));
        resultsContainer.innerHTML = '';

        if (!results || results.length === 0) {
            resultsContainer.innerHTML = '<p>Ничего не найдено.</p>';
            return;
        }

        for (const item of results) {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            resultItem.setAttribute('data-source-video', item.source_video);
            resultItem.setAttribute('data-timestamp', item.timestamp);
            resultItem.setAttribute('data-fps', item.fps);

            const thumbUrl = `${apiBaseUrl}/thumbnail/${item.thumbnail_path.replace(/\\/g, '/')}`;

            if (displayMode === 'image') {
                // Только миниатюра + таймкод + размер
                const img = document.createElement('img');
                img.src = thumbUrl;
                img.onerror = () => { img.src = 'https://via.placeholder.com/120x80.png?text=No+Preview'; };
                resultItem.appendChild(img);

                // Таймкод
                const timeP = document.createElement('p');
                timeP.className = 'timestamp';
                timeP.textContent = `Таймкод: ${item.timestamp || 'N/A'}`;
                resultItem.appendChild(timeP);

                // Размер файла
                const sizeSpan = document.createElement('span');
                sizeSpan.className = 'result-size';
                getImageSize(thumbUrl).then(size => {
                    if (size) sizeSpan.textContent = `Размер: ${size}`;
                });
                resultItem.appendChild(sizeSpan);
            } else if (displayMode === 'text') {
                // Только текст + таймкод, выделяем query
                const descP = document.createElement('p');
                descP.className = 'description';
                descP.innerHTML = highlightText(item.description || 'Нет описания.', query);
                resultItem.appendChild(descP);

                const timeP = document.createElement('p');
                timeP.className = 'timestamp';
                timeP.textContent = `Таймкод: ${item.timestamp || 'N/A'}`;
                resultItem.appendChild(timeP);
            } else {
                // Обычный режим: миниатюра + описание + таймкод
                const img = document.createElement('img');
                img.src = thumbUrl;
                img.onerror = () => { img.src = 'https://via.placeholder.com/120x80.png?text=No+Preview'; };
                resultItem.appendChild(img);

                const infoDiv = document.createElement('div');
                infoDiv.className = 'info';

                const descP = document.createElement('p');
                descP.className = 'description';
                descP.textContent = item.description || 'Нет описания.';

                const timeP = document.createElement('p');
                timeP.className = 'timestamp';
                timeP.textContent = `Таймкод: ${item.timestamp || 'N/A'}`;

                infoDiv.appendChild(descP);
                infoDiv.appendChild(timeP);
                resultItem.appendChild(infoDiv);
            }

            resultItem.addEventListener('click', function() {
                // Если есть In и Out — импортируем диапазон, если Out нет — только In
                if (item.in_timecode && item.source_video) {
                    if (item.out_timecode) {
                        importMediaWithInOut(
                            item.source_video,
                            item.in_timecode,
                            item.out_timecode,
                            item.fps
                        );
                    } else {
                        // Импорт только по In (до конца файла)
                        importMediaWithInOut(
                            item.source_video,
                            item.in_timecode,
                            '',
                            item.fps
                        );
                    }
                } else {
                    /* alert(
                        'Нет данных для In/Out!\\n' +
                        'in_timecode: ' + item.in_timecode + '\\n' +
                        'out_timecode: ' + item.out_timecode + '\\n' +
                        'source_video: ' + item.source_video + '\\n' +
                        'fps: ' + item.fps
                    ); */
                }
            });

            resultsContainer.appendChild(resultItem);
        }
    }

    function importMedia(filePath, timecode, fps) {
        if (!filePath) {
            // alert('Не указан путь к исходному видеофайлу.');
            return;
        }
        console.log(`Requesting to import: ${filePath} at ${timecode}`);
        // Вызываем функцию ExtendScript для импорта
        csInterface.evalScript(`importMediaAndCreateMarker('${filePath.replace(/\\/g, '/')}', '${timecode}', '${fps}')`, (result) => {
            if (result.startsWith("Error:")) {
                // alert(`Ошибка при импорте: ${result}`);
            } else {
                console.log(result); // Log success message from ExtendScript
            }
        });
    }

    // По умолчанию режим all
    setActiveMode('all');
}; 