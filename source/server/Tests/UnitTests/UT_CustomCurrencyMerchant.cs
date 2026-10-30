using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    public class UT_CustomCurrencyMerchant
    {
        [Test]
        public void CurrencyComesFromTheListRow()
        {
            Assert.That(GameCustomCurrencyMerchant.CurrencyKeyFor(new DbOfflineCurrencyList { CurrencyItem = " grove_token " }), Is.EqualTo("grove_token"));
        }

        [Test]
        public void MissingOrBlankRowMeansNoCurrency()
        {
            Assert.That(GameCustomCurrencyMerchant.CurrencyKeyFor(null), Is.Null);
            Assert.That(GameCustomCurrencyMerchant.CurrencyKeyFor(new DbOfflineCurrencyList { CurrencyItem = "  " }), Is.Null);
        }
    }
}
