 function createChart(divId, title, series){
    $(divId).highcharts({
        title: { text: '' },
        chart: {
            type: "line",
            zoomType: "x"
        },
        plotOptions: {
            series: {
                marker: {
                    enabled: false
                }
            }
        },
        legend: {
            layout: 'vertical',
            align: 'right',
            verticalAlign: 'middle',
            borderWidth: 0
        },
        xAxis: {
            type: "datetime",
            min: Date.UTC(2005, 2, 12),
            plotLines: [{
                color: 'grey',
                label: { text: 'sarge' },
                value: Date.UTC(2005, 5, 6),
                width: 1,
            },{
                color: 'grey',
                label: { text: 'etch' },
                value: Date.UTC(2007, 3, 8),
                width: 1,
            },{
                color: 'grey',
                label: { text: 'lenny' },
                value: Date.UTC(2009, 1, 15),
                width: 1,
            },{
                color: 'grey',
                label: { text: 'squeeze' },
                value: Date.UTC(2011, 1, 6),
                width: 1,
            },{
                color: 'grey',
                label: { text: 'wheezy' },
                value: Date.UTC(2013, 4, 4),
                width: 1,
            },],
        },
        yAxis: {
            min: 0,
        },
        series: series
    });
}

function toggleSeries(){
    var archs = [];
    $('input[name="arch"]:checked').each(function(){
        archs.push($(this).val());
    });

    var dists = [];
    $('input[name="dist"]:checked').each(function(){
        dists.push($(this).val());
    });

    $('.chart').each(function(index, chart){
        $.each($(chart).highcharts().series, function(index, one_series){
            var shouldBeVisible = $.inArray(one_series.options.distribution, dists) !== -1 &&
                                  $.inArray(one_series.options.architecture, archs) !== -1;

            if (one_series.visible !== shouldBeVisible){
                one_series.setVisible(shouldBeVisible);
            }
        });
    });

}

$(function () {
    var data = chart_data;

    var package_chart_data = [];
    var maintainer_chart_data = [];
    var size_chart_data = [];
    var avg_size_chart_data = [];
    var pack_ratio_chart_data = [];
    $.each(data.metrics, function(dist_name, arches){
        $.each(arches, function(arch_name, metrics){
            var visible = dist_name === 'testing' && arch_name === 'amd64';

            package_chart_data.push({
                name: dist_name + ' ' + arch_name,
                data: metrics.pkg,
                distribution: dist_name,
                architecture: arch_name,
                visible: visible,
            });

            maintainer_chart_data.push({
                name: dist_name + ' ' + arch_name,
                data: metrics.maintainer,
                distribution: dist_name,
                architecture: arch_name,
                visible: visible,
            });

            size_chart_data.push({
                name: dist_name + ' ' + arch_name + ' total packed size',
                data: metrics.total_packed_size,
                distribution: dist_name,
                architecture: arch_name,
                visible: visible,
            });
            size_chart_data.push({
                name: dist_name + ' ' + arch_name + ' total installed size',
                data: metrics.total_installed_size,
                distribution: dist_name,
                architecture: arch_name,
                visible: visible,
            });

            avg_size_chart_data.push({
                name: dist_name + ' ' + arch_name + ' average packed size',
                data: metrics.avg_packed_size,
                distribution: dist_name,
                architecture: arch_name,
                visible: visible,
            });
            avg_size_chart_data.push({
                name: dist_name + ' ' + arch_name + ' average installed size',
                data: metrics.avg_installed_size,
                distribution: dist_name,
                architecture: arch_name,
                visible: visible,
            });

            pack_ratio_chart_data.push({
                name: dist_name + ' ' + arch_name + ' avg pack ratio',
                data: metrics.avg_pack_ratio,
                distribution: dist_name,
                architecture: arch_name,
                visible: visible,
            });
        });
    });

    createChart('#chart_package', 'Number of packages', package_chart_data);
    createChart('#chart_maintainer', 'Number of maintainers', maintainer_chart_data);
    createChart('#chart_size', 'Package size and installed size', size_chart_data);
    createChart('#chart_avg_size', 'Average package size and average installed size', avg_size_chart_data);
    createChart('#chart_pack_ratio', 'Ratio: package size / install size', pack_ratio_chart_data);
});

