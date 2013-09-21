$(function () {

    function realTopScroll(scroll) {
        scroll = scroll || $(window).scrollTop();
        if (scroll < 0) return 0;
        var maxScroll = $(document).height() - $(window).height();
        if (scroll > maxScroll) return maxScroll;
        return scroll;
    }

    function realLeftScroll(scroll) {
        scroll = scroll || $(window).scrollLeft();
        if (scroll < 0) return 0;
        var maxScroll = $(document).width() - $(window).width();
        if (scroll > maxScroll) return maxScroll;
        return scroll;
    }

    function isSet(obj) {
        return obj != null && typeof obj != 'undefined';
    }

    function getTypeValueName(typeValueId, type) {
        var tvName = CONFIG[type + 's'][typeValueId];
        return isSet(tvName) ? tvName : typeValueId;
    }


    function TrialResultsTable(table, fixedColumnNb) {

        this._fixedColumnNb = fixedColumnNb;

        this._table = $(table);

        this._fixedHeader = null;

        this._fixedColumns = null;

        this._shadowDist = 1;

        this._cloneColumns(this._fixedColumnNb);

        this._cloneHeader();

    }

    TrialResultsTable.prototype = {

        _createInfoCell: function (headerCol, rowValues) {
            var mbn,
                newCol = $('<th></th>');
            newCol.attr('column-type', 'info');
            newCol.attr('info', headerCol.attr('info'));
            if (headerCol.attr('info') == 'block_number') {
                mbn = rowValues.measure_block_number;
                newCol.html(isSet(mbn) ? mbn : '');
                newCol.addClass('column-block-num');
            } else {
                newCol.addClass('column-trial-num');
                newCol.html(rowValues.number);
            }
            this._addEvenOdd(newCol, headerCol);
            return newCol;
        },

        _addEvenOdd: function (cell, headerCol) {
            if (headerCol.hasClass('odd')) {
                cell.addClass('odd');
            } else {
                cell.addClass('even');
            }
        },


        _createStdCell: function (headerCol, values, type) {
            var newCol = $('<td></td>'),
                tId = headerCol.attr(type),
                tvId = values[tId],
                tvName = getTypeValueName(tvId, type);

            newCol.addClass('column-' + tId + '-' + type);
            this._addEvenOdd(newCol, headerCol);
            newCol.attr('column-type', type);
            newCol.attr(type, tId);
            newCol.html(tvName);
            return newCol;
        },

        _createFactorCell: function (headerCol, rowValues) {
            return this._createStdCell(headerCol, rowValues.factors, 'factor');
        },

        _createMeasureCell: function (headerCol, rowValues) {
            return this._createStdCell(headerCol, rowValues.measures, 'measure');
        },

        _createNewRow: function (rowValues) {
            var newRow = $('<tr></tr>'),
                trial = rowValues.number,
                block = rowValues.block_number;
            newRow.attr('trial-number', trial);
            newRow.attr('block-number', block);
            newRow.attr('id', 'trial-results-' + trial + '-' + block);
            return newRow;
        },

        _adjustHeaders: function () {
            var th, thi, fixedTh,
                tHead = this._table.find('thead'),
                ths = tHead.find('th'),
                fixedThs = this._fixedHeader.find('th'),
                thWidth, tick, gap, tickPosition;
            for (thi = 0; thi < ths.length; thi++) {
                th = $(ths[thi]);
                fixedTh = $(fixedThs[thi]);
                thWidth = th.width();
                // adjust width
                fixedTh.css({
                    'min-width': thWidth,
                    'max-width': thWidth,
                    'width': thWidth
                });
                // adjust tick
                tick = fixedTh.find('.tick');
                if (tick.length > 0) {
                    tickPosition = tick.position();
                    gap = th.outerWidth() - tickPosition.left - Math.floor(parseInt(tick.css('width')) / 2);
                    tick.css({
                        left: fixedTh.offset().left + tickPosition.left + gap
                    });
                }
            }
        },


        _cloneColumns: function (fixedColumnNumber) {
            var newTable = $(this._table.clone()),
                rows = this._table.find('tr'),
                newRows = newTable.find('tr'),
                rowCount = rows.length,
                cellCount, rowNum, cellNum, newRow, row, cells,
                tableOffset = this._table.offset();

            newTable.addClass('fixed-columns');
            $('body').append(newTable);

            newTable.css({
                // position: 'fixed', // already in the CSS
                top: tableOffset.top, // -1 for the spacer height
                left: tableOffset.left
            });

            // remove all non fixed columns
            for (rowNum = 0; rowNum < rowCount; rowNum++) {
                row = $(rows.get(rowNum));
                newRow = $(newRows.get(rowNum));
                cells = newRow.find('th, td');
                cellCount = cells.length;
                for (cellNum = fixedColumnNumber; cellNum < cellCount; cellNum++) {
                    $(cells.get(cellNum)).remove();
                }
                this._adjustFixedColumnsRowHeight(row, newRow);
                this._putRowHoverHandler(row, newRow);
            }

            this._fixedColumns = newTable;
            this._adjustFixedColumnsWidth();
            this._putFixedColsScrollHandler();
        },

        _putFixedColsScrollHandler: function () {
            var fixedCols = this._fixedColumns,
                tableTop = this._table.offset().top,
                rgbaRegex = /[^,]+(?=\))/,
                shadowMax = 0,
                shadowCss,
                shadowDist = this._shadowDist,
                initLeft = fixedCols.offset().left,
                lastTopScroll = null,
                lastLeftScroll = null;

            fixedCols.addClass('shadowed');
            shadowCss = fixedCols.css('box-shadow');
            if (shadowCss && shadowCss != 'none') shadowMax = parseFloat(shadowCss.match(rgbaRegex)[0]);
            else shadowCss = null;
            fixedCols.removeClass('shadowed');

            function move() {
                var top = fixedCols.offset().top,
                    newTop = parseInt(fixedCols.css('top')) - top + tableTop;
                fixedCols.css('top', newTop);
            }

            function adjustShadow(scroll) {
                var shadowFactor, newShadowCss,
                    left = Math.min(initLeft - scroll, initLeft);
                shadowFactor = Math.min(shadowDist, Math.max(0, shadowDist - left - shadowDist)) / shadowDist;
                newShadowCss = shadowCss.replace(rgbaRegex, shadowMax * shadowFactor);
                fixedCols.addClass('shadowed')
                fixedCols.css('box-shadow', newShadowCss);
                if (shadowFactor == 0) fixedCols.removeClass('shadowed');
            }

            $(window).scroll(function () {
                var leftScroll,
                    topScroll = realTopScroll();
                if (topScroll !== lastTopScroll) {
                    move();
                    lastTopScroll = topScroll;
                }
                if (shadowCss) {
                    leftScroll = realLeftScroll()
                    if (leftScroll != lastLeftScroll) {
                        adjustShadow(leftScroll);
                        lastLeftScroll = leftScroll;
                    }
                }
            });
        },

        _putRowHoverHandler: function (row1, row2) {
            var $row1 = $(row1), $row2 = $(row2);

            function doIt(row1, row2) {
                row1.hover(function () {
                    row2.addClass('hovered');
                }, function () {
                    row2.removeClass('hovered');
                });
            }

            doIt($row1, $row2);
            doIt($row2, $row1);
        },

        _adjustFixedColumnsWidth: function () {
            var rows = this._fixedColumns.find('tr'),
                origRows = this._table.find('tr'),
                width, origCell;
            rows.each(function (rowNum, row) {
                var origRow = origRows.get(rowNum),
                    cells = $(row).find('td, th'),
                    origCells = $(origRow).find('td, th');
                cells.each(function (cellNum, fixedCell) {
                    origCell = origCells.get(cellNum);
                    width = origCells.width();
                    $(fixedCell).css({
                        width: width,
                        'min-width': width,
                        'max-width': width
                    });
                });

            });

        },

        _adjustFixedColumnsRowHeight: function (originalRow, fixedRow) {
            var height = $(originalRow).height();
            $(fixedRow).css({
                height: height
            });
        },

        _addFixedColumnsNewRow: function (row) {
            var fixedRow = row.clone(),
                colCount = this._fixedColumnNb,
                cellNum = 0;
            this._fixedColumns.first('tbody').append(fixedRow);
            fixedRow.find('th, td').each(function () {
                if (cellNum >= colCount) this.remove();
                cellNum++;
            });
            this._adjustFixedColumnsRowHeight(row, fixedRow);
            this._putRowHoverHandler(row, fixedRow);
        },


        _cloneHeader: function () {
            var tHead = this._table.find('thead'),
                newTHead = tHead.clone(),
                newTable = $('<table class="gridtable fixed-header" ></table>'),
                tHeadOffset = tHead.offset(),
                newCols = newTHead.find('th,td'),
                cols = tHead.find('th,td'),
                colNum, newCol, nextCol = null, tick;
            $('body').append(newTable);
            newTable.append(newTHead);

            newTable.css({
                // position: 'fixed', // already in the CSS
                top: tHeadOffset.top, // -1 for the spacer height
                left: tHeadOffset.left
            });

            newTHead.css({
                'border-bottom-style': 'solid',
                'border-bottom-width': 2,
                'border-color': this._table.css('border-color'),
                'width': this._table.outerWidth()
            });

            for (colNum = 0; colNum < cols.length; colNum++) {
                newCol = nextCol || $(newCols[colNum]);
                newCol.tooltipster({
                    speed: 200,
                    delay: 0,
                    position: 'bottom',
                    content: "<b>" + newCol.attr('column-type') + ":</b> " + newCol.attr(newCol.attr('column-type'))
                });
                nextCol = $(newCols[colNum + 1]);
                // add the tick
                if (nextCol.length > 0) {
                    tick = $('<div class="tick"></div>');
                    if (newCol.attr('column-type') != nextCol.attr('column-type')) {
                        tick.css('width', 2);
                    }
                    newCol.append(tick);
                }
            }

            this._fixedHeader = newTable;

            this._adjustHeaders()

            newTable.addClass('shadowed')
            var initTop = parseInt(newTable.css('top')),
                container = $("#container"),
                rgbaRegex = /[^,]+(?=\))/,
                shadowCss = newTable.css('box-shadow'),
                shadowMax = parseFloat(shadowCss.match(rgbaRegex)[0]),
                shadowDist = this._shadowDist,
                lastTopScroll = null,
                lastLeftScroll = null;
            newTable.removeClass('shadowed');

            function moveTop(top) {
                newTable.css('top', top);
            }

            function moveLeft() {
                var left = newTable.offset().left,
                    newLeft = parseInt(newTable.css('left')) - left + tHeadOffset.left;
                newTable.css('left', newLeft);
            }

            function adjustShadow(top) {
                var shadowFactor = Math.min(shadowDist, Math.max(0, shadowDist - top - shadowDist)) / shadowDist,
                    newShadowCss = shadowCss.replace(rgbaRegex, shadowMax * shadowFactor);
                newTable.css('box-shadow', newShadowCss);
                if (shadowFactor == 0) newTable.removeClass('shadowed')
                else newTable.addClass('shadowed');
            }

            $(window).scroll(function () {
                var topScroll = realTopScroll(),
                    leftScroll,
                    topRaw = initTop - topScroll,
                    top = Math.max(topRaw, 0);
                if (topScroll !== lastTopScroll) {
                    moveTop(top);
                    if (shadowCss) adjustShadow(topRaw);
                    lastTopScroll = topScroll;
                } else {
                    leftScroll = realLeftScroll()
                    if (leftScroll != lastLeftScroll) moveLeft();
                }
            });
        },

        addRow: function (rowValues) {
            var col, colNum,
                tr = this._table.find("#trial-results-header"),
                cols = tr.find("th"),
                colCount = cols.length,
                tBody = this._table.find("tbody"),
                newRow = this._createNewRow(rowValues),
                tableWidth = this._table.width();
            newRow.appendTo(tBody);
            for (colNum = 0; colNum < colCount; colNum++) {
                col = $(cols[colNum]);
                switch (col.attr('column-type')) {
                    case 'info':
                        newRow.append(this._createInfoCell(col, rowValues));
                        break;
                    case 'factor' :
                        newRow.append(this._createFactorCell(col, rowValues))
                        break;
                    case 'measure' :
                        newRow.append(this._createMeasureCell(col, rowValues))
                        break
                }

            }
            this._addFixedColumnsNewRow(newRow);
            if (this._table.width() != tableWidth) {
                this._adjustHeaders();
                this._adjustFixedColumnsWidth();
            }
        }
    };

    var trt = new TrialResultsTable($('#trial-results'), 2),
        wsAddr = "ws://" + location.hostname + (location.port ? ':' + location.port : '') + CONFIG.websocket_url,
        ws = new WebSocket(wsAddr),
        animBottom = false;

    ws.onopen = function () {
        console.log("Socket opened.");
    };
    ws.onmessage = function (msg) {
        console.log(msg);
        var row = JSON.parse(msg.data),
            scrollBottom = $(window).scrollTop() + $(window).height(),
            onBottom = scrollBottom >= $(document).height();

        trt.addRow(row);

        if (onBottom || animBottom) {
            $('html, body').stop(true, true);
            $('html, body').animate({
                scrollTop: $(document).height() - $(window).height()
            }, {
                always: function () {
                    animBottom = false;
                }
            });
            animBottom = true;
        }
    };


    $(window).on('mousewheel touchstart mousedown', function () {
        $('html, body').stop();
    });

    ws.onerror = ws.onclose = function (err) {
        // TODO: fix that
//        $('#message').html('(disconnected)');
//        $('#container').animate({
//            'padding-top': 99
//        }, 'fast');
//        $('#title').animate({
//            'padding-bottom': 40
//        }, 'fast');
//        $('#message').show();
    };

    $(window).scroll(function () {
        var scroll = realTopScroll();
        $('#title').css('top', -scroll);
    })
});