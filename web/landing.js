'use strict';
// A badge name is a lookup/onboarding hint, never a verified invitation or identity.
const invitation = document.getElementById('repository-invitation');
const handoff = TipjarModel.parseRepositoryHandoff(location.search);
if (handoff.invalid) {
  invitation.hidden = false;
  invitation.textContent =
    'This repository link is not recognized. Use the board or local directory to explore.';
} else if (handoff.repository !== null) {
  invitation.hidden = false;
  const context = document.createElement('span');
  context.textContent =
    'From your link: ' + handoff.repository + '. This is not a verified invitation. ';
  const prepare = document.createElement('a');
  prepare.textContent = 'Prepare README invitation for ' + handoff.repository + ' ↗';
  prepare.href = 'directory.html?repo=' + encodeURIComponent(handoff.repository) + '#maintainers';
  const lookup = document.createElement('a');
  lookup.textContent = 'Look for this project on the public board ↗';
  lookup.href = TipjarModel.repositoryHandoffURL(location.href, handoff);
  invitation.append(context, prepare, document.createTextNode(' · '), lookup);
}
