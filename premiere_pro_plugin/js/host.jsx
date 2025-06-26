function timecodeToSeconds(timecode, fps) {
    if (!timecode || typeof timecode !== 'string') {
        return 0;
    }
    
    var parts = timecode.split(/[:.]/);
    if (parts.length !== 4) return 0;

    var hours = parseInt(parts[0], 10);
    var minutes = parseInt(parts[1], 10);
    var seconds = parseInt(parts[2], 10);
    var framesOrMs = parseInt(parts[3], 10);

    var totalSeconds = (hours * 3600) + (minutes * 60) + seconds;

    // Определяем, последнее значение - это кадры или миллисекунды
    if (timecode.indexOf('.') !== -1) { // Вместо includes
        totalSeconds += framesOrMs / 1000.0;
    } else {
        if (fps > 0) {
            totalSeconds += framesOrMs / fps;
        }
    }
    
    return totalSeconds;
}

function findProjectItem(proj, filePath) {
    var fileName = File(filePath).name;
    var fileNameNoExt = fileName.split('.')[0];
    var found = null;
    function searchItem(item) {
        if (item.type === ProjectItemType.CLIP) {
            // Сравниваем по имени файла (точно и без расширения)
            if (item.name === fileName || item.name.split('.')[0] === fileNameNoExt) {
                found = item;
                return;
            }
            // Сравниваем по getMediaPath (с учетом прямых/обратных слэшей)
            var mediaPath = item.getMediaPath();
            if (mediaPath && (mediaPath.replace(/\\/g, '/').toLowerCase() === filePath.replace(/\\/g, '/').toLowerCase())) {
                found = item;
                return;
            }
        }
        // Рекурсивно ищем во вложенных папках
        if (item.children && item.children.numItems > 0) {
            for (var i = 0; i < item.children.numItems; i++) {
                searchItem(item.children[i]);
                if (found) return;
            }
        }
    }
    searchItem(proj.rootItem);
    return found;
}

function importMediaAndCreateMarker(filePath, timecode, fps) {
    try {
        if (filePath === 'undefined' || !filePath) {
            return "Error: File path is not specified.";
        }
        
        var file = new File(filePath);
        if (!file.exists) {
            return "Error: File does not exist at path: " + filePath;
        }

        var proj = app.project;
        if (!proj) {
            return "Error: No project is open.";
        }

        // 1. Импортируем файл в проект
        proj.importFiles([filePath], true, null, false);
        
        // 2. Добавляем на активную таймлинию
        var sequence = proj.activeSequence;
        if (!sequence) {
             return "Success (no sequence): File imported into project bin. Please open a sequence to add it to the timeline.";
        }

        // --- Новый блок: повторный поиск импортированного файла с задержкой и альтернативой по имени ---
        var projectItem = null;
        var maxTries = 20;
        var delayMs = 1000;
        var fileName = File(filePath).name;
        var fileNameNoExt = fileName.split('.')[0];
        for (var attempt = 0; attempt < maxTries; attempt++) {
            for (var i = 0; i < proj.rootItem.children.numItems; i++) {
                var item = proj.rootItem.children[i];
                // Сравниваем по getMediaPath, по имени файла и по имени без расширения
                if ((item.type === ProjectItemType.CLIP && item.getMediaPath() === filePath) ||
                    (item.type === ProjectItemType.CLIP && item.name === fileName) ||
                    (item.type === ProjectItemType.CLIP && item.name.split('.')[0] === fileNameNoExt)) {
                    projectItem = item;
                    break;
                }
            }
            if (projectItem) {
                break;
            }
            $.sleep(delayMs);
        }
        // --- Конец нового блока ---
        
        if (!projectItem) {
             return "Error: Could not find the imported item in the project bin.";
        }

        // Вставляем клип в конец первого видео трека
        var videoTrack = sequence.videoTracks[0];
        if (videoTrack) {
            videoTrack.insertClip(projectItem, sequence.end);
        } else {
            return "Error: No video tracks in the active sequence.";
        }
        
        // 3. Создаем маркер
        if (timecode && timecode !== 'undefined') {
            var markerTimeInSeconds = timecodeToSeconds(timecode, parseFloat(fps));

            // Находим клип на таймлинии (последний добавленный)
            var trackClip = videoTrack.clips[videoTrack.clips.numItems - 1];

            if (trackClip) {
                var markers = trackClip.getMarkers();
                var newMarker = markers.createMarker(markerTimeInSeconds);
                newMarker.name = "Кадр из архива";
                newMarker.comments = "Таймкод: " + timecode;
                
                // Для Premiere Pro 2022 и новее можно задать цвет
                if (parseFloat(app.version) >= 15) {
                   newMarker.setColorByIndex(4); // Зеленый
                }
            }
        }

        return "Success: Media imported and marker added.";

    } catch (e) {
        return "Error: " + e.toString();
    }
}

function importMediaWithInOut(filePath, inTimecode, outTimecode, fps) {
    try {
        if (filePath === 'undefined' || !filePath) {
            return "Error: File path is not specified.";
        }
        var file = new File(filePath);
        if (!file.exists) {
            return "Error: File does not exist at path: " + filePath;
        }
        var proj = app.project;
        if (!proj) {
            return "Error: No project is open.";
        }
        proj.importFiles([filePath], true, null, false);
        var sequence = proj.activeSequence;
        if (!sequence) {
            return "Success (no sequence): File imported into project bin. Please open a sequence to add it to the timeline.";
        }
        var maxTries = 20;
        var delayMs = 1000;
        var projectItem = null;
        for (var attempt = 0; attempt < maxTries; attempt++) {
            projectItem = findProjectItem(proj, filePath);
            if (projectItem) {
                break;
            }
            $.sleep(delayMs);
        }
        if (!projectItem) {
            return "Error: Could not find the imported item in the project bin.";
        }
        // Устанавливаем In/Out
        if (inTimecode) {
            var inSec = timecodeToSeconds(inTimecode, parseFloat(fps));
            projectItem.setInPoint(inSec, 4);
        }
        if (outTimecode && outTimecode !== '' && outTimecode !== 'end') {
            var outSec = timecodeToSeconds(outTimecode, parseFloat(fps));
            projectItem.setOutPoint(outSec, 4);
        }
        /* alert(
          'DEBUG\\nfilePath: ' + filePath +
          '\\ninTimecode: ' + inTimecode +
          '\\noutTimecode: ' + outTimecode +
          '\\nfps: ' + fps +
          '\\nprojectItem: ' + (projectItem ? projectItem.name : 'NOT FOUND') +
          '\\ngetMediaPath: ' + (projectItem ? projectItem.getMediaPath() : 'N/A')
        ); */
        var videoTrack = sequence.videoTracks[0];
        if (videoTrack) {
            videoTrack.insertClip(projectItem, sequence.end);
        } else {
            return "Error: No video tracks in the active sequence.";
        }
        return "Success: Media imported with In/Out.";
    } catch (e) {
        return "Error: " + e.toString();
    }
} 