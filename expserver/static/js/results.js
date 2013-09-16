$(function () {

    function TrialResultsTable(table, factors, measures) {
        this._table = table;
        this._factors = factors;
        this._measures = measures;
    }

    TrialResultsTable.prototype = {
        addRow: function (rowValues) {

        }
    };

    new TrialResultsTable($('#trial-results'), RUN_INFOS.factors, RUN_INFOS.measures);

});