if __name__ == '__main__':
    import argparse
    import sys
    from gevent.pywsgi import WSGIServer
    from lightmill.queryyesno import query_yes_no
    from lightmill.app import create_app, import_experiment
    import lightmill.default_settings as default_settings

    parser = argparse.ArgumentParser(description='Experiment server.')

    parser.add_argument('-p', '--port',
                        type=int,
                        default=default_settings.SERVER_PORT,
                        help='Server port.')
    parser.add_argument('-e', '--experiment-design',
                        type=open,
                        help='Experiment design file to import on startup'
                             ' (if the experiment is not already imported).'
                             ' Supports touchsTone\'s XML export format.')
    parser.add_argument('-d', '--database',
                        default=default_settings.DATABASE_URI,
                        type=str,
                        help='Database file path'
                             ' (default: {}).'.format(default_settings.DATABASE_URI))
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        default=False,
                        help='Print out SQL requests.')
    parser.add_argument('--debug',
                        default=False,
                        action='store_true',
                        help='Server debug mode. Provides error trace from the browser on server'
                             ' errors.')
    parser.add_argument('--fixed-measures',
                        default=False,
                        action='store_true',
                        help='Prevent recording measures that are not defined in the experiment'
                             ' design. Pushing trial results containing unknown measures will'
                             ' result in an error.')
    parser.add_argument('--unprotected-runs',
                        default=False,
                        action='store_true',
                        help='Allow ongoing runs to be re-allocated (i.e. run locks are '
                             ' unprotected and always acquired when requested).'
                             ' This allows a run client to disconnect and reconnect (e.g. by'
                             ' refreshing a page) without unlocking its run.'
                             ' WARNING: this allows a client to "steal" the run of another.'
                             ' DO NOT USE IN PRODUCTION.')
    parser.add_argument('--volatile',
                        default=False,
                        action='store_true',
                        help='Do not keep any data. WARNING: This is only useful during'
                             ' development. DO NOT USE IN PRODUCTION. The data cannot be exported'
                             ' in any way.')

    args = parser.parse_args()

    if args.volatile or args.unprotected_runs:
        if not query_yes_no('WARNING: \'--unprotected-runs\' and \'--volatile\' are unfit for'
                            ' production and must not be used during an actual experiment.'
                            ' Continue ?',
                            default="no"):
            sys.exit(0)

    app = create_app(database_uri=args.database,
                     sql_echo=args.verbose,
                     debug=args.debug,
                     do_not_protect_runs=args.unprotected_runs,
                     add_missing_measures=not args.fixed_measures,
                     volatile=args.volatile)

    # Load experiment_design if provided.
    experiment_design = args.experiment_design
    if experiment_design:
        import_experiment(app, experiment_design)

    print('* Running on http://0.0.0.0:{} (Press CTRL+C to quit)'.format(args.port))
    try:
        http_server = WSGIServer(('0.0.0.0', args.port), app)
        http_server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
