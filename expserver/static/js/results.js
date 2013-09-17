$(function () {

    function realScroll(scroll){
        scroll = scroll || $(window).scrollTop();
        if(scroll < 0) return 0;
        var maxScroll = $(document).height()-$(window).height();
        if(scroll > maxScroll) return maxScroll;
        return scroll;
    }

    function isSet(obj) {
        return obj != null && typeof obj != 'undefined';
    }

    function getTypeValueName(typeValueId, type) {
        var tvName = CONFIG[type + 's'][typeValueId];
        return isSet(tvName) ? tvName : typeValueId;
    }


    function TrialResultsTable(table) {
        this._table = $(table);

        this._fixedHeader = null;

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

        _adjustHeaderWidths: function () {
            var th, thi, cellSpacer, fixedTh,
                tHead = this._table.find('thead'),
                ths = tHead.find('th'),
                fixedThs = this._fixedHeader.find('th'),
                thWidth;
            for (thi = 0; thi < ths.length; thi++) {
                th = $(ths[thi]);
                fixedTh = $(fixedThs[thi]);
                thWidth = th.outerWidth();
                cellSpacer = $(fixedThs[thi]).find('.cell-spacer');
                cellSpacer.width(fixedTh.outerWidth());
                var gap = fixedTh.outerWidth() - thWidth;
                cellSpacer.width(cellSpacer.width() - gap);
            }
        },

        _cloneHeader: function () {
            var tHead = this._table.find('thead'),
                newTHead = tHead.clone(),
                newTable = $('<table class="gridtable fixedheader" ></table>'),
                tHeadOffset = tHead.offset(),
                newCols = newTHead.find('th,td'),
                cols = tHead.find('th,td'),
                colNum, col, newCol, cellSpacer;
            $('body').append(newTable);
            newTable.append(newTHead);
            newTHead.css({
                'border-bottom-style': 'solid',
                'border-bottom-width': 2,
                'border-color': this._table.css('border-color')
            });

            // append the spacers to the columns
            for (colNum = 0; colNum < cols.length; colNum++) {
                newCol = $(newCols[colNum]);
                col = $(cols[colNum]);
                cellSpacer = $('<div class="cell-spacer"></div>');
                newCol.prepend(cellSpacer);
            }

            newTable.css({
                position: 'fixed',
                top: tHeadOffset.top - 1, // -1 for the spacer height
                left: tHeadOffset.left
            });
            this._fixedHeader = newTable;

            this._adjustHeaderWidths()

            var initTop = parseInt(newTable.css('top')),
                container = $("#container");
            $(window).scroll(function () {

                var scroll = realScroll(),
                    left = newTable.offset().left,
                    newLeft = parseInt(newTable.css('left')) - left + tHeadOffset.left;
                newTable.css('left', newLeft);
                newTable.css('top', Math.min(Math.max(initTop - scroll, 0), initTop));
            });
        },

        addRow: function (rowValues) {
            var col, colNum, newCol,
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
            if (this._table.width() != tableWidth) this._adjustHeaderWidths();

        }
    };

    var trt = new TrialResultsTable($('#trial-results')),
        wsAddr = "ws://" + location.hostname + (location.port ? ':' + location.port : '') + CONFIG.websocket_url,
        ws = new WebSocket(wsAddr),
        bottomDiv = $('#bottom'),
        animBottom = false;

    ws.onopen = function () {
        console.log("Socket opened.");
    };
    ws.onmessage = function (msg) {
        var onbottom = bottomDiv.is(':appeared') || animBottom;
        console.log(msg);
        var row = JSON.parse(msg.data);
        trt.addRow(row);
        if (onbottom) {
            animBottom = true
            $('html, body').stop(true, true);
            $('html, body').animate({
                scrollTop: bottomDiv.offset().top
            }, {
                always: function () {
                    animBottom = false;
                }
            });
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
        var scroll = realScroll();
        $('#title').css('top', -scroll);
    })
});