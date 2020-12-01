import os

c.CourseDirectory.course_id = os.environ.get("NAAS_COURSE_ID", "missing")

# c.Exchange.root = '/tmp/exchange'

c.ExchangeFactory.collect = 'nbexchange.plugin.ExchangeCollect'

## A plugin for exchange.
c.ExchangeFactory.exchange = 'nbexchange.plugin.Exchange'

## A plugin for fetching assignments.
c.ExchangeFactory.fetch_assignment = 'nbexchange.plugin.ExchangeFetchAssignment'

## A plugin for fetching feedback.
c.ExchangeFactory.fetch_feedback = 'nbexchange.plugin.ExchangeFetchFeedback'

## A plugin for listing exchange files.
c.ExchangeFactory.list = 'nbexchange.plugin.ExchangeList'

## A plugin for releasing assignments.
c.ExchangeFactory.release_assignment = 'nbexchange.plugin.ExchangeReleaseAssignment'

## A plugin for releasing feedback.
c.ExchangeFactory.release_feedback = 'nbexchange.plugin.ExchangeReleaseFeedback'

## A plugin for submitting assignments.
c.ExchangeFactory.submit = 'nbexchange.plugin.ExchangeSubmit'


# We want downloads to be ./course123/ps1 not ./ps1
c.Exchange.path_includes_course = True