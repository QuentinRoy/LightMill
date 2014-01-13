window.StrokeDrawer = (function () {


    function isSet(a) {
        return a !== null && typeof a !== 'undefined';
    }

    function StrokeDrawer(targetCanvas, xColumn, yColumn, timesColumn, events) {
        this._canvas = targetCanvas;
        this._context = this._canvas.getContext('2d');
        this._x = xColumn;
        this._y = yColumn;
        this._time = timesColumn;
        this._events = events;
        this._currentDrawnTime = 0;

    }

    StrokeDrawer.prototype = {
        get currentDrawnTime() {
            return this._currentDrawnTime;
        },

        _draw: function (starttime, endtime) {
            var i, event, time, x, y,
                n = this._events.length;
            for (i = 0; i < n; i++) {
                event = this._events[i];
                time = event[this._time];
                x = parseInt(event[this._x], 10);
                y = parseInt(event[this._y], 10);
                if ((!isSet(starttime) || time > starttime) && (!isSet(endtime) || time <= endtime)) {
                    if (i <= 0) {
                        this._context.arc(x, y,6,0,2*Math.PI);
                        this._context.fillStyle='#5C0600';
                        this._context.fill();
                        this._context.beginPath();
                        this._context.moveTo(x, y);
                    } else {
                        this._context.lineTo(x, y);
                    }
                }
                this._currentDrawnTime = time;
            }
            this._context.lineWidth=4;
            this._context.lineCap='round';
            this._context.stroke();
        },


        draw: function (time, redraw) {
            if ((!isSet(time) || time > this.currentDrawnTime) && !redraw) {
                this._draw(this.currentDrawnTime, time)
            } else {
                this._context.clearRect(0, 0, this._canvas.width, this._canvas.height);
                this._draw(0, time);
            }
        },

        getTimeWindow: function () {
            return [
                this._events[0][this._time],
                this._events[this._events.length - 1][this._time]
            ];

        }


    };

    return StrokeDrawer;

}());
