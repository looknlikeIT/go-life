odoo.define('website_pbo.slider_price', function (require) {
'use strict';

var Widget = require('web.Widget');
var websiteRootData = require('website.WebsiteRoot');

var sliderPrice = Widget.extend({
    slider: false,

    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        this.slider = document.getElementById('sliderPrice');

        var conf = {
            start: [this.$el.data('current-min') || 0, this.$el.data('current-max') || 10000],
            connect: true,
            tooltips: [wNumb({decimals: 0}), wNumb({decimals: 0})],
            range: {
                'min': this.$el.data('slider-min') || 0,
                'max': this.$el.data('slider-max') || 10000,
            }
        }
        noUiSlider.create(this.slider, conf);
        this.slider.noUiSlider.on('change.one', function (o) {
            var input = self.$el.data('input');
            var newRange = o[0] + '-' + o[1];
            $(input).val(newRange);
            $(input).change()
        });
        return def;
    },
});

websiteRootData.websiteRootRegistry.add(sliderPrice, '.sliderPrice');
return LazyTemplateRenderer;

})