if __name__ == '__main__':
    from application_factory import app

    app.run(debug=True,
            threaded=True,
            host=app.settings['SERVER'].get('host'),
            port=app.settings['SERVER'].getint('port'),
            use_reloader=False)

    # Exiting -------
    if app.settings['SERVER'].getboolean('onion_server'):
        from tor import stop_hidden_services
        stop_hidden_services(app)
