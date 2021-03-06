(function (requirejs, require, define) {

/*
"This is as true in everyday life as it is in battle: we are given one life
and the decision is ours whether to wait for circumstances to make up our
mind, or whether to act, and in acting, to live."
— Omar N. Bradley
 */

// VideoProgressSlider module.
define(
'video/06_video_progress_slider.js',
[],
function () {

    // VideoProgressSlider() function - what this module "exports".
    return function (state) {
        state.videoProgressSlider = {};

        _makeFunctionsPublic(state);
        _renderElements(state);
        // No callbacks to DOM events (click, mousemove, etc.).
    };

    // ***************************************************************
    // Private functions start here.
    // ***************************************************************

    // function _makeFunctionsPublic(state)
    //
    //     Functions which will be accessible via 'state' object. When called,
    //     these functions will get the 'state' object as a context.
    function _makeFunctionsPublic(state) {
        state.videoProgressSlider.onSlide        = _.bind(onSlide, state);
        state.videoProgressSlider.onStop         = _.bind(onStop, state);
        state.videoProgressSlider.updatePlayTime = _.bind(
            updatePlayTime, state
        );

        //Added for tests -- JM
        state.videoProgressSlider.buildSlider = _.bind(buildSlider, state);

        state.videoProgressSlider.updateStartEndTimeRegion = _.bind(
            updateStartEndTimeRegion, state
        );
    }

    // function _renderElements(state)
    //
    //     Create any necessary DOM elements, attach them, and set their
    //     initial configuration. Also make the created DOM elements available
    //     via the 'state' object. Much easier to work this way - you don't
    // have to do repeated jQuery element selects.
    function _renderElements(state) {
        if (!onTouchBasedDevice()) {
            state.videoProgressSlider.el = state.videoControl.sliderEl;

            buildSlider(state);
            _buildHandle(state);
        }
    }

    function _buildHandle(state) {
        state.videoProgressSlider.handle = state.videoProgressSlider.el
            .find('.ui-slider-handle');

        // ARIA
        // We just want the knob to be selectable with keyboard
        state.videoProgressSlider.el.attr('tabindex', -1);
        // Let screen readers know that this anchor, representing the slider
        // handle, behaves as a slider named 'video position'.
        state.videoProgressSlider.handle.attr({
            'role': 'slider',
            'title': 'video position',
            'aria-disabled': false,
            'aria-valuetext': getTimeDescription(state.videoProgressSlider
                .slider.slider('option', 'value'))
        });
    }

    // ***************************************************************
    // Public functions start here.
    // These are available via the 'state' object. Their context ('this'
    // keyword) is the 'state' object. The magic private function that makes
    // them available and sets up their context is makeFunctionsPublic().
    // ***************************************************************

    function buildSlider(state) {
        state.videoProgressSlider.slider = state.videoProgressSlider.el
            .slider({
                range: 'min',
                slide: state.videoProgressSlider.onSlide,
                stop: state.videoProgressSlider.onStop
            });

        state.videoProgressSlider.sliderProgress = state.videoProgressSlider
            .slider
            .find('.ui-slider-range.ui-widget-header.ui-slider-range-min');
    }

    function updateStartEndTimeRegion(params) {
        var left, width, start, end;

        // We must have a duration in order to determine the area of range.
        // It also must be non-zero.
        if (!params.duration) {
            return;
        }

        // If the range spans the entire length of video, we don't do anything.
        if (!this.config.start && !this.config.end) {
            return;
        }

        start = this.config.start;

        // If end is set to null, then we set it to the end of the video. We
        // know that start is not a the beginning, therefore we must build a
        // range.
        end = this.config.end || params.duration;

        left = (100 * (start / params.duration)).toFixed(1);
        width = (100 * ((end - start) / params.duration)).toFixed(1);

        if (!this.videoProgressSlider.sliderRange) {
            this.videoProgressSlider.sliderRange = $('<div />', {
                class: 'ui-slider-range ' +
                       'ui-widget-header ' +
                       'ui-corner-all ' +
                       'slider-range'
            }).css({
                left: left + '%',
                width: width + '%'
            });

            this.videoProgressSlider.sliderProgress
                .after(this.videoProgressSlider.sliderRange);
        } else {
            this.videoProgressSlider.sliderRange
                .css({
                    left: left + '%',
                    width: width + '%'
                });
        }
    }

    function onSlide(event, ui) {
        this.videoProgressSlider.frozen = true;

        this.trigger(
            'videoPlayer.onSlideSeek',
            {'type': 'onSlideSeek', 'time': ui.value}
        );

        // ARIA
        this.videoProgressSlider.handle.attr(
            'aria-valuetext', getTimeDescription(this.videoPlayer.currentTime)
        );
    }

    function onStop(event, ui) {
        var _this = this;

        this.videoProgressSlider.frozen = true;

        this.trigger(
            'videoPlayer.onSlideSeek',
            {'type': 'onSlideSeek', 'time': ui.value}
        );

        // ARIA
        this.videoProgressSlider.handle.attr(
            'aria-valuetext', getTimeDescription(this.videoPlayer.currentTime)
        );

        setTimeout(function() {
            _this.videoProgressSlider.frozen = false;
        }, 200);
    }

    // Changed for tests -- JM: Check if it is the cause of Chrome Bug Valera
    // noticed
    function updatePlayTime(params) {
        if (
            (this.videoProgressSlider.slider) &&
            (!this.videoProgressSlider.frozen)
        ) {
            this.videoProgressSlider.slider
                .slider('option', 'max', params.duration)
                .slider('option', 'value', params.time);
        }
    }

    // Returns a string describing the current time of video in hh:mm:ss
    // format.
    function getTimeDescription(time) {
        var seconds = Math.floor(time),
            minutes = Math.floor(seconds / 60),
            hours = Math.floor(minutes / 60),
            hrStr, minStr, secStr;

        seconds = seconds % 60;
        minutes = minutes % 60;

        hrStr = hours.toString(10);
        minStr = minutes.toString(10);
        secStr = seconds.toString(10);

        if (hours) {
            hrStr += (hours < 2 ? ' hour ' : ' hours ');

            if (minutes) {
                minStr += (minutes < 2 ? ' minute ' : ' minutes ');
            } else {
                minStr += ' 0 minutes ';
            }

            if (seconds) {
                secStr += (seconds < 2 ? ' second ' : ' seconds ');
            } else {
                secStr += ' 0 seconds ';
            }

            return hrStr + minStr + secStr;
        } else if (minutes) {
            minStr += (minutes < 2 ? ' minute ' : ' minutes ');

            if (seconds) {
                secStr += (seconds < 2 ? ' second ' : ' seconds ');
            } else {
                secStr += ' 0 seconds ';
            }

            return minStr + secStr;
        } else if (seconds) {
            secStr += (seconds < 2 ? ' second ' : ' seconds ');

            return secStr;
        }

        return '0 seconds';
    }

});

}(RequireJS.requirejs, RequireJS.require, RequireJS.define));
