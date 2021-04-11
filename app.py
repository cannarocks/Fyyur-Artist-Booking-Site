# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import dateutil.parser
import datetime
import babel
from flask import Flask, render_template, request, Response, jsonify, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from forms import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website_link = db.Column(db.String(), nullable=True)
    image_link = db.Column(db.String(500))
    genres = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.Text, nullable=True)
    shows = db.relationship("Show", cascade="all,delete", backref="venue", lazy=True)

    def __repr__(self):
        return f'<Venue {self.id} {self.name}>'


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.Text)
    shows = db.relationship("Show", cascade="all,delete", backref="artist", lazy=True)

    def __repr__(self):
        return f'<Artist {self.id} {self.name}>'


class Show(db.Model):
    __tablename__ = "Show"

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Show {self.id} {self.artist.name}>'


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(str(value))
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# Prepare data for Venues and artists
def get_data_with_shows(data):
    if data is not None:
        data.genres = data.genres.split(', ')
        data.past_shows, data.upcoming_shows = [], []
        data.past_shows_count, data.upcoming_shows_count = 0, 0

        if len(data.shows):
            for show in data.shows:
                if show.start_time > datetime.now():
                    data.upcoming_shows_count += 1
                    data.upcoming_shows.append(show)
                else:
                    data.past_shows.append(show)
                    data.past_shows_count += 1

    return data


# Populate form with data retrieved from db
def populate_form(form, obj):
    if form is not None and obj is not None:
        for field in form.data:
            if hasattr(obj, field):
                form_field = getattr(form, field)
                value = getattr(obj, field)
                form_field.data = value


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data, areas = {}, []

    for venue in Venue.query.all():
        num_shows, num_upcoming_shows = 0, 0

        if data.get(venue.city) is None:
            data[venue.city] = {'city': '', 'state': '', 'venues': []}
            data[venue.city]['city'] = venue.city
            data[venue.city]['state'] = venue.state
            # data[venue.city].venues = []

        if len(venue.shows):
            for show in venue.shows:
                num_shows += 1
                if show.start_time > datetime.now():
                    num_upcoming_shows += 1

        venue.num_upcoming_shows = num_upcoming_shows
        data[venue.city]['venues'].append(venue)

    for key in data:
        areas.append(data[key])

    return render_template('pages/venues.html', areas=areas)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    term = request.form.get('search_term', '').lower()

    data = Venue.query.filter(
        or_(
            func.lower(Venue.city).like(f'%{term}%'),
            func.lower(Venue.state).like(f'%{term}%'),
            func.lower(Venue.name).like(f'%{term}%')
        )
    )

    return render_template('pages/search_venues.html', results={
        "count": data.count(),
        "data": data
    }, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    data = get_data_with_shows(Venue.query.get(venue_id))

    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False

    try:
        venue = Venue(
            name=request.form.get('name'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            address=request.form.get('address'),
            phone=request.form.get('phone'),
            website_link=request.form.get('website_link'),
            image_link=request.form.get('image_link'),
            genres=', '.join(request.form.getlist('genres')),
            facebook_link=request.form.get('facebook_link'),
            seeking_talent=request.form.get('seeking_talent') == 'y',
            seeking_description=request.form.get('seeking_description')
        )

        db.session.add(venue)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        error = True
        print(logging.error("Fatal error: " + str(e)))
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    else:
        flash('Venue ' + request.form['name'] + ' was successfully listed!')

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    success = True
    error = ''
    venue = Venue.query.get(venue_id)

    try:
        db.session.delete(venue)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        success = False
        print(logging.error("Fatal error: " + str(e)))
    finally:
        db.session.close()

    if success:
        flash('Venue ' + venue.name + ' was successfully deleted!')
    else:
        error = 'An error occurred. Venue ' + venue.name + ' could not be deleted.'
        flash(error)

    # return render_template('pages/home.html')
    return jsonify({'success': success, 'error': error})


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    return render_template('pages/artists.html', artists=Artist.query.all())


@app.route('/artists/search', methods=['POST'])
def search_artists():
    term = request.form.get('search_term', '').lower()

    data = Artist.query.filter(func.lower(Artist.name).like(f'%{term}%'))

    return render_template('pages/search_artists.html', results={
        "count": data.count(),
        "data": data
    }, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    artist = get_data_with_shows(Artist.query.get(artist_id))

    return render_template('pages/show_artist.html', artist=artist)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)

    # Populate form
    populate_form(form, artist)

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    artist = Artist.query.get(artist_id)
    error = False

    try:
        artist.name = request.form.get('name')
        artist.city = request.form.get('city')
        artist.state = request.form.get('state')
        artist.phone = request.form.get('phone')
        artist.website_link = request.form.get('website_link')
        artist.image_link = request.form.get('image_link')
        artist.genres = ', '.join(request.form.getlist('genres'))
        artist.facebook_link = request.form.get('facebook_link')
        artist.seeking_venue = request.form.get('seeking_venue') == 'y'
        artist.seeking_description = request.form.get('seeking_description')

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        error = True
        print(logging.error("Fatal error: " + str(e)))
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Artist ' + request.form.get('name') + ' could not be updated.')
    else:
        flash('Artist ' + request.form.get('name') + ' was successfully updated!')

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)

    # Populate form
    populate_form(form, venue)

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.get(venue_id)
    error = False

    try:
        venue.name = request.form.get('name')
        venue.city = request.form.get('city')
        venue.state = request.form.get('state')
        venue.address = request.form.get('address')
        venue.phone = request.form.get('phone')
        venue.website_link = request.form.get('website_link')
        venue.image_link = request.form.get('image_link')
        venue.genres = ', '.join(request.form.getlist('genres'))
        venue.facebook_link = request.form.get('facebook_link')
        venue.seeking_talent = request.form.get('seeking_talent') == 'y'
        venue.seeking_description = request.form.get('seeking_description')

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        error = True
        print(logging.error("Fatal error: " + str(e)))
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue ' + request.form.get('name') + ' could not be updated.')
    else:
        flash('Venue ' + request.form.get('name') + ' was successfully updated!')

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False

    try:
        artist = Artist(
            name=request.form.get('name'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            phone=request.form.get('phone'),
            website_link=request.form.get('website_link'),
            image_link=request.form.get('image_link'),
            genres=', '.join(request.form.getlist('genres')),
            facebook_link=request.form.get('facebook_link'),
            seeking_venue=request.form.get('seeking_venue') == 'y',
            seeking_description=request.form.get('seeking_description')
        )

        db.session.add(artist)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        error = True
        print(logging.error("Fatal error: " + str(e)))
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
    else:
        flash('Artist ' + request.form['name'] + ' was successfully listed!')

    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    return render_template('pages/shows.html', shows=Show.query.all())


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    artist = request.form.get('artist_id')
    venue = request.form.get('venue_id')
    date = request.form.get('start_time')
    error = False

    try:
        show = Show(artist_id=artist, venue_id=venue, start_time=date)
        db.session.add(show)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        error = True
        print(logging.error("Fatal error: " + str(e)))
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Show could not be listed.', 'error')
    else:
        flash('Show was successfully listed!')

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
