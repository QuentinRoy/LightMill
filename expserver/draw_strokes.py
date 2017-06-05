from flask import Flask
from expserver.model import Trial, Experiment, db, Block, Run, Measure
import os
import cairo
import math


DRAW_CIRCLE = True
PRINT_FACTORS = False
MARK_CENTER = True
DRAW_START_ANGLE = True

FACTOR_HEIGHT = 30 if PRINT_FACTORS else 0
TEXT_PADDING = 8
WIDTH, HEIGHT = 768, 928
DEFAULT_DRAW_STROKE = True
DEFAULT_DRAW_POINTS = True
STROKE_WIDTH = 2
POINT_WIDTH = 6
CENTER_CROSS_WIDTH = 10
CENTER_LINE_WIDTH = 2
STROKE_PATHS = 'export/strokes'


def trial_measure(measure_id, trial):
    return trial.measure_values.join(Measure).filter(Measure.id == measure_id).one().value


class Circle:
    def __init__(self, center, radius):
        self.center = center
        self.radius = radius

    def calc_right(self):
        return self.center[0] + self.radius

    def calc_left(self):
        return self.center[0] - self.radius

    def calc_top(self):
        return self.center[1] - self.radius

    def calc_bottom(self):
        return self.center[1] + self.radius

    def draw(self, context):
        context.set_dash([1, 0])
        context.set_source_rgb(0.9, 0.9, 0.9)
        # x_value = trial.measure_values.join(Measure).filter(Measure.id == 'circle.center.x').one().value
        x, y = self.center
        radius = self.radius
        context.arc(x, y, radius, 0, 2 * math.pi)
        context.fill()


class Stroke:
    def __init__(self, points, circle, start_angle):
        self.points = points
        self.circle = circle
        self.start_angle = start_angle

    def first(self):
        return self.points[0]

    def calc_left(self):
        left = None
        for point in self.points:
            if not left or point[0] < left:
                left = point[0]
        return max(left, self.circle.calc_left())

    def calc_top(self):
        top = None
        for point in self.points:
            if not top or point[1] < top:
                top = point[1]
        return max(top, self.circle.calc_top())

    def calc_bottom(self):
        bottom = 0
        for point in self.points:
            if point[1] > bottom:
                bottom = point[1]
        return max(bottom, self.circle.calc_bottom())

    def calc_right(self):
        right = 0
        for point in self.points:
            if point[0] > right:
                right = point[0]
        return max(right, self.circle.calc_right())

    def empty(self):
        return len(self.points) <= 0

    def zeroed(self, new_left, new_top):
        left = self.calc_left()
        top = self.calc_top()
        new_stroke = [(point[0] - left + new_left, point[1] - top + new_top) for point in self._points]
        new_circle = Circle([self.circle.center[0] - left + new_left, self.circle.center[1] - top + new_top],
                            self.circle.radius)
        return Stroke(new_stroke, new_circle)

    @classmethod
    def from_trial(cls, trial):
        stroke = []
        for event in trial.events:
            state = event.measure_values['pointer.state'].value
            if state != 'end':
                x = int(event.measure_values['pointer.x'].value)
                y = int(event.measure_values['pointer.y'].value)
                stroke.append((x, y))
        if stroke:
            circle_center = tuple(float(trial_measure('circle.center.' + coord, trial)) for coord in ('x', 'y'))
            radius = float(trial_measure('circle.radius', trial))
            startAngle = float(trial_measure('circle.radius', trial))
            return cls(stroke, Circle(circle_center, radius), startAngle)
        else:
            return cls(stroke, None, None)

    def draw(self, context, draw_points=DEFAULT_DRAW_POINTS, draw_stroke=DEFAULT_DRAW_STROKE):

        # draw start point
        first_x, first_y = self.first()
        context.set_source_rgb(0.7, 0, 0)
        context.move_to(first_x, first_y)
        context.arc(first_x, first_y, 8, 0, 2 * math.pi)
        context.fill()

        # draw points
        if draw_points:
            context.set_source_rgb(0, 0, 0)
            for x, y in self.points:
                context.move_to(x, y)
                context.arc(x, y, POINT_WIDTH/2, 0, 2 * math.pi)
                context.fill()

        # draw stroke
        if draw_stroke:
            context.set_source_rgb(0, 0, 0)
            context.set_line_width(STROKE_WIDTH)
            context.set_dash([1, 0])
            context.set_line_cap(cairo.LINE_CAP_ROUND)
            context.set_line_join(cairo.LINE_JOIN_ROUND)
            started = False
            for x, y in self.points:
                if not started:
                    context.move_to(x, y)
                    started = True
                else:
                    context.line_to(x, y)
            context.stroke()


def print_factors(trial, context):
    context.set_source_rgb(0, 0, 0)
    context.rectangle(0, HEIGHT, WIDTH, HEIGHT + FACTOR_HEIGHT)
    context.fill()

    context.select_font_face("Sans",
                             cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)
    font_size = FACTOR_HEIGHT - TEXT_PADDING * 2
    context.set_font_size(font_size)
    context.set_source_rgb(1, 1, 1)
    context.move_to(TEXT_PADDING, HEIGHT / 2 + font_size / 4)
    value_strings = []
    for factor_value in trial.iter_all_factor_values():
        factor_id = factor_value.factor.id
        value = factor_value.id
        value_strings.append("{}: {}".format(factor_id, value))
    print(', '.join(value_strings))
    context.show_text(', '.join(value_strings))


def draw_cross(position, context):
    width = CENTER_CROSS_WIDTH
    context.set_source_rgb(0, 0, 0.5)
    context.set_line_width(CENTER_LINE_WIDTH)
    context.set_dash([1, 0])
    context.set_line_cap(cairo.LINE_CAP_ROUND)
    context.move_to(position[0] - width / 2, position[1])
    context.line_to(position[0] + width / 2, position[1])
    context.move_to(position[0], position[1] - width / 2)
    context.line_to(position[0], position[1] + width / 2)
    context.stroke()


def draw_start_angle(stroke, context):
    # draw line
    center_x, center_y = stroke.circle.center
    context.set_source_rgb(0.1, 0.6, 0.1)
    context.set_line_cap(cairo.LINE_CAP_ROUND)
    context.set_line_width(STROKE_WIDTH)
    context.set_dash([3, 6], 0)
    context.move_to(center_x, center_y)
    context.line_to(*stroke.first())
    context.stroke()

    # center circle
    context.set_source_rgb(0.95, 0.95, 0.95)
    context.arc(center_x, center_y, 16, 0, 2 * math.pi)
    context.fill()

    # writing
    context.select_font_face("Sans",
                             cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)
    context.set_font_size(14)
    context.set_source_rgb(0.1, 0.6, 0.1)
    text = u"{}".format(int(round(stroke.start_angle)))
    x_bearing, y_bearing, width, height, x_advance, y_advance = context.text_extents(text)
    text_x = center_x - (width / 2 + x_bearing)
    text_y = center_y - (height / 2 + y_bearing)
    context.move_to(text_x, text_y)
    context.show_text(text)


def draw_trial(trial, img_path):
    print('Draw trial: {}-{}'.format(trial.block.number, trial.number))
    print('path: {}'.format(img_path))
    ps = cairo.PDFSurface(img_path, WIDTH, HEIGHT + (FACTOR_HEIGHT if PRINT_FACTORS else 0))
    # ps.set_fallback_resolution(2000, 2000)
    cr = cairo.Context(ps)

    stroke = Stroke.from_trial(trial)

    if PRINT_FACTORS:
        print_factors(trial, cr)
    if not stroke.empty():
        if DRAW_CIRCLE:
            stroke.circle.draw(cr)
        if DRAW_START_ANGLE:
            draw_start_angle(stroke, cr)
        stroke.draw(cr)

    if MARK_CENTER:
        draw_cross([WIDTH / 2, HEIGHT / 2], cr)


def export_run_strokes2(run, base_filter={}, path=STROKE_PATHS):
    trials = Trial.query.options(db.joinedload(Trial.block)) \
        .join(Block, Run).order_by(Block.number, Trial.number) \
        .filter(Block.run == run, Block.practice == False).all()

    if not os.path.exists(path):
        os.makedirs(path)

    for startAngle in [u'free'] + [u"{}".format(angle) for angle in range(0, 360, 45)]:
        this_filter = {
            u'startAngle': [startAngle]
        }
        this_filter.update(base_filter)
        for trial in trials:
            for factor_value in trial.iter_all_factor_values():
                factor_id = factor_value.factor.id
                value_id = factor_value.id
                f_filter = this_filter.get(factor_id, None)
                if f_filter and not value_id in f_filter:
                    break
            else:
                img_path = os.path.join(path,
                                        "{}-{}-{}-{}.pdf".format(startAngle, run.id, trial.block.measured_block_number(),
                                                                 trial.number))
                img_path = os.path.abspath(img_path)
                draw_trial(trial, img_path)


def export_run_strokes(run, path=STROKE_PATHS, base_filter={}):
    trials = Trial.query.options(db.joinedload(Trial.block)) \
        .join(Block, Run).order_by(Block.number, Trial.number) \
        .filter(Block.run == run, Block.practice == False).all()

    if not os.path.exists(path):
        os.makedirs(path)

    for trial in trials:
        for factor_value in trial.iter_all_factor_values():
            factor_id = factor_value.factor.id
            value_id = factor_value.id
            f_filter = base_filter.get(factor_id, None)
            if f_filter and not value_id in f_filter:
                break
        else:
            img_path = os.path.join(path,
                                    "{}-{}-{}.pdf".format(run.id, trial.block.measured_block_number(),
                                                             trial.number))
            img_path = os.path.abspath(img_path)
            draw_trial(trial, img_path)


def main(data_path):
    app = Flask(__name__.split('.')[0])
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath(
        os.path.join(os.path.dirname(__file__), data_path))

    # database initialization
    db.init_app(app)
    db.app = app

    for run in Experiment.query.first().runs:
        export_run_strokes(run)

def main2(data_path):

    filter = {
        u"size": [u'free'],
        u"rotDir": [u'-1', u'antitrigo'],
        u"revolutions": [u'1'],
        u"endAngle": [u'free'],
        # u'startAngle': [u'0'],
        u"endDir": [u'free']
    }


    app = Flask(__name__.split('.')[0])
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath(
        os.path.join(os.path.dirname(__file__), data_path))

    # database initialization
    db.init_app(app)
    db.app = app

    for run in Experiment.query.first().runs:
        export_run_strokes2(run, filter)

def main3(data_path):
    app = Flask(__name__.split('.')[0])
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath(
        os.path.join(os.path.dirname(__file__), data_path))

    # database initialization
    db.init_app(app)
    db.app = app

    first_x = []
    first_y = []
    for run in Experiment.query.first().runs:
        trials = Trial.query.options(db.joinedload(Trial.block)) \
            .join(Block, Run).order_by(Block.number, Trial.number) \
            .filter(Block.run == run).all()
        for trial in trials:
            stroke = Stroke.from_trial(trial)
            mbn = trial.block.measured_block_number()
            row = [mbn if mbn else '', trial.number]
            if not stroke.empty():
                row += [x for x in stroke.points[-1]]
            else:
                row += ['','']
            print(','.join("{}".format(c) for c in row))


if __name__ == '__main__':
    # main2('../PiloteThibaut.db')
    main2('../piloteGilles.db')
