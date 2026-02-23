import { useEffect } from 'react';
import { useNavigate } from 'react-router';
import { detectLanguage } from '~/lib/i18n';

const LanguageRedirect = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const language = detectLanguage();
    navigate(`/${language}`, { replace: true });
  }, [navigate]);

  return null;
};

export default LanguageRedirect;
